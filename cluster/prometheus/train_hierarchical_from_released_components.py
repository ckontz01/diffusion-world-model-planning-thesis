#!/usr/bin/env python3

"""Train Hi-LeWM using the released model/config/helper components.

The Zenodo artifact accidentally packages the evaluator at
``h_le_wm/train/hierarchical.py``.  This entry point reconstructs only the
missing orchestration layer.  Architecture, forward/loss functions, waypoint
sampling, preprocessing, configuration, and checkpoint classes come from the
released artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from copy import deepcopy
from functools import partial
from pathlib import Path

import hydra
import lightning as pl
import stable_pretraining as spt
import stable_worldmodel as swm
import torch
from lightning.pytorch.callbacks import Callback, ModelCheckpoint
from omegaconf import OmegaConf, open_dict

from h_le_wm.baseline.adapter import (
    ARPredictor,
    SIGReg,
    get_column_normalizer,
    get_img_preprocessor,
)
from h_le_wm.models.jepa import HiJEPA
from h_le_wm.train.pretrained import load_pretrained_low_level_model
from h_le_wm.train.steps import (
    build_macro_action_encoder,
    clone_projection_head,
    hi_lejepa_forward_p2_frozen,
    is_p2_frozen_optimization_enabled,
)
from h_le_wm.train.waypoint_ops import build_p2_frozen_waypoint_collate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_spt_resize_api_compatibility() -> dict:
    """Bridge stable-pretraining 0.1.8 to torchvision 0.20's method name.

    ``spt.data.transforms.Resize.__call__`` invokes ``self.transform``.  The
    torchvision v2 base class bundled with the frozen PyTorch 2.5.1 container
    exposes that identical operation as ``self._transform``.  Alias only the
    missing public name; the released Resize object, parameters, interpolation,
    antialiasing, and tensor kernel remain unchanged.
    """

    resize_cls = spt.data.transforms.Resize
    if callable(getattr(resize_cls, "transform", None)):
        mode = "native_transform"
    elif callable(getattr(resize_cls, "_transform", None)):
        resize_cls.transform = resize_cls._transform
        mode = "alias_transform_to__transform"
    else:
        raise RuntimeError(
            "stable-pretraining Resize exposes neither transform nor _transform"
        )
    summary = {
        "mode": mode,
        "stable_pretraining_version": importlib.metadata.version(
            "stable-pretraining"
        ),
        "torchvision_version": importlib.metadata.version("torchvision"),
        "resize_class": f"{resize_cls.__module__}.{resize_cls.__name__}",
    }
    print(f"[hierarchical-train-repair] resize API compatibility: {summary}")
    return summary


class AtomicObjectCheckpoint(Callback):
    """Save the inference model object at the released epoch naming scheme."""

    def __init__(self, run_dir: Path, model_name: str, epoch_interval: int = 1):
        super().__init__()
        self.run_dir = Path(run_dir)
        self.model_name = str(model_name)
        self.epoch_interval = int(epoch_interval)

    def on_train_epoch_end(self, trainer, pl_module):
        if not trainer.is_global_zero:
            return
        epoch = int(trainer.current_epoch) + 1
        if epoch % self.epoch_interval != 0 and epoch != int(trainer.max_epochs):
            return
        self.run_dir.mkdir(parents=True, exist_ok=True)
        destination = self.run_dir / f"{self.model_name}_epoch_{epoch}_object.ckpt"
        partial_path = destination.with_name(destination.name + ".partial")
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite object checkpoint: {destination}")
        if partial_path.exists():
            partial_path.unlink()
        torch.save(pl_module.model, partial_path)
        with partial_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(partial_path, destination)
        print(
            f"[hierarchical-train-repair] saved {destination} "
            f"sha256={sha256_file(destination)}"
        )


def compose_config(config_root: Path, data_name: str, args) -> object:
    with hydra.initialize_config_dir(
        version_base=None, config_dir=str(config_root.resolve())
    ):
        cfg = hydra.compose(config_name="hi_lewm", overrides=[f"data={data_name}"])
    with open_dict(cfg):
        cfg.output_model_name = args.output_model_name
        cfg.subdir = str(args.output_dir)
        cfg.seed = int(args.seed)
        cfg.trainer.max_epochs = int(args.max_epochs)
        cfg.trainer.devices = 1
        cfg.trainer.accelerator = "gpu"
        cfg.loader.batch_size = int(args.batch_size)
        cfg.loader.num_workers = int(args.num_workers)
        cfg.loader.persistent_workers = int(args.num_workers) > 0
        cfg.pretrained_low_level.checkpoint.selection_mode = "explicit_path"
        cfg.pretrained_low_level.checkpoint.path = str(args.base_checkpoint)
        cfg.wm.high_level.latent_action_dim = int(args.latent_action_dim)
        cfg.wandb.enabled = False
    return cfg


def build_dataset_and_loaders(cfg, args):
    dataset = swm.data.HDF5Dataset(**cfg.data.dataset, transform=None)
    pixel_preprocessor = get_img_preprocessor(
        source="pixels", target="pixels", img_size=int(cfg.img_size)
    )
    transforms = []
    with open_dict(cfg):
        for column in cfg.data.dataset.keys_to_load:
            if str(column).startswith("pixels"):
                continue
            transforms.append(get_column_normalizer(dataset, column, column))
        cfg.wm.action_dim = int(cfg.data.dataset.frameskip) * int(
            dataset.get_dim("action")
        )

    if not is_p2_frozen_optimization_enabled(cfg):
        raise ValueError(
            "This repair is frozen to the released low-level-frozen fast path"
        )
    dataset.transform = (
        spt.data.transforms.Compose(*transforms) if transforms else None
    )
    collate_fn = build_p2_frozen_waypoint_collate(cfg, pixel_preprocessor)

    generator = torch.Generator().manual_seed(int(cfg.seed))
    train_set, val_set = spt.data.random_split(
        dataset,
        lengths=[float(cfg.train_split), 1.0 - float(cfg.train_split)],
        generator=generator,
    )
    loader_kwargs = OmegaConf.to_container(cfg.loader, resolve=True)
    loader_kwargs["collate_fn"] = collate_fn
    train_loader = torch.utils.data.DataLoader(
        train_set,
        **loader_kwargs,
        shuffle=True,
        drop_last=True,
        generator=generator,
    )
    val_loader = torch.utils.data.DataLoader(
        val_set,
        **loader_kwargs,
        shuffle=False,
        drop_last=False,
    )
    dataset_summary = {
        "dataset_type": f"{type(dataset).__module__}.{type(dataset).__name__}",
        "dataset_rows": len(dataset),
        "train_rows": len(train_set),
        "validation_rows": len(val_set),
        "episode_count": len(dataset.lengths),
        "native_action_dim": int(dataset.get_dim("action")),
        "frameskip": int(cfg.data.dataset.frameskip),
        "model_action_dim": int(cfg.wm.action_dim),
        "num_steps": int(cfg.data.dataset.num_steps),
    }
    return train_loader, val_loader, dataset_summary


def build_hierarchical_model(cfg, base_checkpoint: Path) -> HiJEPA:
    base = load_pretrained_low_level_model(base_checkpoint)
    latent_action_dim = int(cfg.wm.high_level.latent_action_dim)
    embed_dim = int(cfg.wm.embed_dim)
    action_dim = int(cfg.wm.action_dim)
    num_high_frames = int(cfg.wm.high_level.waypoints.num) - 1

    predictor_cfg = OmegaConf.to_container(cfg.predictor_high, resolve=True)
    high_predictor = ARPredictor(
        num_frames=num_high_frames,
        input_dim=embed_dim,
        hidden_dim=embed_dim,
        output_dim=embed_dim,
        **predictor_cfg,
    )
    latent_action_encoder = build_macro_action_encoder(
        cfg, input_dim=action_dim, latent_dim=latent_action_dim
    )
    projection_mode = str(cfg.wm.high_level.macro_to_condition_proj).lower()
    if projection_mode == "identity" or (
        projection_mode == "auto" and latent_action_dim == embed_dim
    ):
        macro_to_condition = torch.nn.Identity()
    elif projection_mode in {"auto", "linear"}:
        macro_to_condition = torch.nn.Linear(latent_action_dim, embed_dim)
    else:
        raise ValueError(f"Unsupported macro_to_condition_proj={projection_mode}")

    model = HiJEPA(
        encoder=base.encoder,
        low_predictor=base.predictor,
        action_encoder=base.action_encoder,
        high_predictor=high_predictor,
        latent_action_encoder=latent_action_encoder,
        macro_to_condition=macro_to_condition,
        projector=base.projector,
        low_pred_proj=base.pred_proj,
        high_pred_proj=clone_projection_head(base.pred_proj),
    )
    freeze_cfg = cfg.pretrained_low_level.freeze
    model.freeze_low_level(
        freeze_encoder=bool(freeze_cfg.encoder),
        freeze_low_predictor=bool(freeze_cfg.low_level_predictor),
        freeze_action_encoder=bool(freeze_cfg.low_level_action_encoder),
        freeze_projector=bool(freeze_cfg.projector),
        freeze_low_pred_proj=bool(freeze_cfg.low_pred_proj),
        freeze_high_pred_proj=bool(freeze_cfg.high_pred_proj),
    )
    return model


def architecture_summary(model: HiJEPA) -> dict:
    module_names = [
        "encoder",
        "low_predictor",
        "action_encoder",
        "high_predictor",
        "latent_action_encoder",
        "macro_to_condition",
        "projector",
        "low_pred_proj",
        "high_pred_proj",
    ]
    return {
        "type": f"{type(model).__module__}.{type(model).__name__}",
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "trainable_parameter_count": sum(
            parameter.numel()
            for parameter in model.parameters()
            if parameter.requires_grad
        ),
        "freeze_flags": dict(model._freeze_flags),
        "modules": {
            name: {
                "type": f"{type(getattr(model, name)).__module__}.{type(getattr(model, name)).__name__}",
                "parameter_count": sum(
                    parameter.numel() for parameter in getattr(model, name).parameters()
                ),
                "trainable_parameter_count": sum(
                    parameter.numel()
                    for parameter in getattr(model, name).parameters()
                    if parameter.requires_grad
                ),
                "state_shapes": {
                    key: list(value.shape)
                    for key, value in getattr(model, name).state_dict().items()
                },
            }
            for name in module_names
        },
    }


def prepare_spt_manual_optimization(trainer: pl.Trainer, module: spt.Module) -> None:
    """Apply stable-pretraining's Manager contract before ``Trainer.fit``.

    Lightning rejects Trainer-level clipping for manual-optimization modules.
    ``spt.Manager`` handles this by stashing the value on suffixed Trainer
    attributes and clearing only the field inspected by Lightning's validator;
    ``spt.Module.on_train_start`` then restores the value per optimizer and its
    manual training loop performs the clipping.  This standalone entry point
    uses the same released-library contract without adopting Manager's unrelated
    run-directory and logging orchestration.
    """

    if getattr(module, "automatic_optimization", True):
        return
    clip_val = trainer.gradient_clip_val
    if clip_val is None or clip_val <= 0:
        return
    trainer.gradient_clip_val_ = clip_val
    trainer.gradient_clip_algorithm_ = trainer.gradient_clip_algorithm
    trainer.gradient_clip_val = None
    print(
        "[hierarchical-train-repair] manual optimization: "
        f"stashed gradient_clip_val={trainer.gradient_clip_val_} "
        f"algorithm={trainer.gradient_clip_algorithm_}; "
        "spt.Module.training_step will apply it"
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-root", type=Path, required=True)
    parser.add_argument("--data-name", default="hi_tworoom")
    parser.add_argument("--base-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-model-name", required=True)
    parser.add_argument("--seed", type=int, default=3072)
    parser.add_argument("--max-epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--num-workers", type=int, default=6)
    parser.add_argument("--latent-action-dim", type=int, default=32)
    parser.add_argument("--limit-train-batches", type=int, default=None)
    parser.add_argument("--limit-val-batches", type=int, default=None)
    parser.add_argument("--resume-from", type=Path, default=None)
    parser.add_argument("--architecture-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_epochs <= 0 or args.batch_size <= 0 or args.num_workers < 0:
        raise ValueError("Invalid training size argument")
    if not args.base_checkpoint.is_file():
        raise FileNotFoundError(args.base_checkpoint)
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to reuse output directory: {args.output_dir}")

    torch.set_float32_matmul_precision("high")
    pl.seed_everything(int(args.seed), workers=True)
    compatibility_summary = install_spt_resize_api_compatibility()
    cfg = compose_config(args.config_root, args.data_name, args)
    train_loader, val_loader, dataset_summary = build_dataset_and_loaders(cfg, args)
    model = build_hierarchical_model(cfg, args.base_checkpoint)
    model_summary = architecture_summary(model)

    # The released PushT epoch-15 checkpoint has these exact architecture counts.
    # TwoRoom has the same base LeWM/action dimensions, so a mismatch means this
    # orchestration repair no longer reconstructs the released architecture.
    if model_summary["parameter_count"] != 30_526_414:
        raise RuntimeError(f"Unexpected total parameter count: {model_summary}")
    if model_summary["trainable_parameter_count"] != 12_491_936:
        raise RuntimeError(f"Unexpected trainable parameter count: {model_summary}")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    OmegaConf.save(cfg, args.output_dir / "effective-config.yaml")
    (args.output_dir / "dataset-summary.json").write_text(
        json.dumps(dataset_summary, indent=2, sort_keys=True) + "\n"
    )
    (args.output_dir / "architecture-summary.json").write_text(
        json.dumps(model_summary, indent=2, sort_keys=True) + "\n"
    )
    (args.output_dir / "compatibility-summary.json").write_text(
        json.dumps(compatibility_summary, indent=2, sort_keys=True) + "\n"
    )
    if args.architecture_only:
        print(json.dumps({"dataset": dataset_summary, "model": model_summary}, indent=2))
        return 0

    optimizers = {
        "model_opt": {
            "modules": "model",
            "optimizer": OmegaConf.to_container(cfg.optimizer, resolve=True),
            "scheduler": {"type": "LinearWarmupCosineAnnealingLR"},
            "interval": "epoch",
        }
    }
    module = spt.Module(
        model=model,
        sigreg=SIGReg(**OmegaConf.to_container(cfg.loss.sigreg.kwargs, resolve=True)),
        forward=partial(hi_lejepa_forward_p2_frozen, cfg=cfg),
        optim=optimizers,
        hparams=OmegaConf.to_container(cfg, resolve=True),
    )

    callbacks = [
        AtomicObjectCheckpoint(
            run_dir=args.output_dir,
            model_name=args.output_model_name,
            epoch_interval=int(cfg.checkpointing.object_dump.epoch_interval),
        ),
        ModelCheckpoint(
            dirpath=args.output_dir / "trainer-checkpoints",
            filename=args.output_model_name + "_epoch_{epoch}",
            every_n_epochs=1,
            save_top_k=-1,
            save_last=True,
        ),
    ]
    trainer_kwargs = OmegaConf.to_container(cfg.trainer, resolve=True)
    trainer_kwargs.update(
        callbacks=callbacks,
        num_sanity_val_steps=1,
        logger=False,
        enable_checkpointing=True,
        default_root_dir=str(args.output_dir),
    )
    if args.limit_train_batches is not None:
        trainer_kwargs["limit_train_batches"] = int(args.limit_train_batches)
    if args.limit_val_batches is not None:
        trainer_kwargs["limit_val_batches"] = int(args.limit_val_batches)
    trainer = pl.Trainer(**trainer_kwargs)
    prepare_spt_manual_optimization(trainer, module)
    ckpt_path = str(args.resume_from) if args.resume_from is not None else None
    trainer.fit(
        module,
        train_dataloaders=train_loader,
        val_dataloaders=val_loader,
        ckpt_path=ckpt_path,
    )

    final_checkpoint = (
        args.output_dir
        / f"{args.output_model_name}_epoch_{int(args.max_epochs)}_object.ckpt"
    )
    if not final_checkpoint.is_file():
        raise FileNotFoundError(f"Final object checkpoint was not created: {final_checkpoint}")
    completion = {
        "status": "complete",
        "final_checkpoint": str(final_checkpoint),
        "final_checkpoint_bytes": final_checkpoint.stat().st_size,
        "final_checkpoint_sha256": sha256_file(final_checkpoint),
    }
    (args.output_dir / "COMPLETE.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(completion, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
