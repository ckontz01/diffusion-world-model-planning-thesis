"""Frozen non-outcome artifact and seed specification for E11."""

from __future__ import annotations

import hashlib
from typing import Any


TASKS = ("pusht", "reacher", "cube")
SEEDS = (6101, 6102, 6103)
ARMS = (
    "b0",
    "acid",
    "reachability",
    "forward",
    "gaussian_select",
    "vp_shuffled_select",
    "vp_unconditional_select",
    "vp_true_select",
)
CORE_ARMS = ("acid", "reachability", "forward")
PROPOSAL_ARMS = (
    "gaussian_select",
    "vp_shuffled_select",
    "vp_unconditional_select",
    "vp_true_select",
)
COUNT = 400
UNTOUCHED_CAPACITY = {"pusht": 1760, "reacher": 956, "cube": 889}
SHARD_SIZE = 50
SHARD_COUNT = 8
CANDIDATE_COUNT = 300
REVERSE_EVALUATIONS = 5
GUIDANCE_SCALE = 1.5
EXPECTED_GPU_NAME = "NVIDIA RTX 6000 Ada Generation"
EXPECTED_HOSTNAME = "gpu09.cluster"
PROTOCOL_SHA256 = "9b4bde9e2f69a7b92abaaf33f9db3016b8f61e82bedbe662a71a054cf3832ce0"
E10M_AGGREGATE_SHA256 = (
    "a685fd9da7f6050a98cdc7fe792d73fec4f83a3e1dc6dd083982fbe5c274f84c"
)
E10M_SOURCE_MANIFEST_SHA256 = (
    "3231a9d92fc7f6ebf333a7a361adafd40c43eb6240fa377710d9eaaa48b12c65"
)
E10V_SOURCE_MANIFEST_SHA256 = (
    "b843a68dda3355499cada1d580853654efa404bc5f5d2375fbee14b4121e3e5d"
)


TASK_SPEC: dict[str, dict[str, Any]] = {
    "pusht": {
        "dataset_name": "pusht_expert_train",
        "dataset_file": "pusht_expert_train.h5",
        "dataset_sha256": "b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb",
        "world_model_policy": "pusht/lewm_hf_22b330c",
        "world_model_file": "pusht/lewm_hf_22b330c_object.ckpt",
        "world_model_sha256": "c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659",
        "scorer_job": 296631,
        "reachability_job": 296633,
        "e10v_indices": {"vp_true": 0, "vp_shuffled_goal": 1},
        "e7_gaussian_index": 2,
        "e10m_base": 0,
    },
    "reacher": {
        "dataset_name": "dmc/reacher_random",
        "dataset_file": "reacher.h5",
        "dataset_sha256": "85a7dddfa1801302abcb175a80a23bb69c78291dd977ce40d69aedcb9123da06",
        "world_model_policy": "reacher/lewm",
        "world_model_file": "reacher/lewm_object.ckpt",
        "world_model_sha256": "6b03b0e39f00a601b83dc94765e4b022c48127ced762543bddb1398ce52c310d",
        "scorer_job": 296650,
        "reachability_job": 296652,
        "e10v_indices": {"vp_true": 2, "vp_shuffled_goal": 3},
        "e7_gaussian_index": 5,
        "e10m_base": 6,
    },
    "cube": {
        "dataset_name": "ogbench/cube_single_expert",
        "dataset_file": "cube_single_expert.h5",
        "dataset_sha256": "0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625",
        "world_model_policy": "cube/lewm_hf_b0747c5",
        "world_model_file": "cube/lewm_hf_b0747c5_object.ckpt",
        "world_model_sha256": "5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07",
        "scorer_job": 296669,
        "reachability_job": 296671,
        "e10v_indices": {"vp_true": 4, "vp_shuffled_goal": 5},
        "e7_gaussian_index": 8,
        "e10m_base": 12,
    },
}


CORE_CHECKPOINT_SHA256 = {
    "pusht": {
        "acid": (
            "6b49d24ab9a3cfdbe4695343f3a9c30723f9ee4d70c892fe603f8e9818b3f9d2",
            "1ae9a988c93321d6de9ffdbb22faebc8289d82f76ae171d51e1754fe9be228f8",
            "d1e293821fd5c20a8bf5f35b0a01a61a3446a4896dbf7d7ccd429d093e00cad8",
        ),
        "reachability": (
            "09e08ef112da2b2280bbed44914bf4041e5cd342095ac9677eb1a3e921050432",
            "f6cc3e440d90ec932f2fe897057ffe63701f8a381ae600fd35732c51ab0da7be",
            "7f5826013d7c7a63a1921f57a82364a02e6e6c7f100e3518df88d8c2d863a027",
        ),
        "forward": (
            "826177bb363e8004ef22b8a4e273135befabf285e416935eed69bd907b479b3b",
            "02f8e229c6bcbdfff50b8604a08486771d315fc4dd7f628cdf3be821f5c2bcc6",
            "d77affdbdc3df8a04d2511b64192e8df9633d624bd1dbfa513d71e7d28add888",
        ),
    },
    "reacher": {
        "acid": (
            "8e0a7bad0f8c9d4ce574fca611d2642e5213e8831e7db0c7b4559939146ae5ab",
            "44cabeb97163fcd3c102a470e4ba146e94633cdd647dd4d02fe8ba6def1edcbd",
            "01c51d787f20514dd5ab00bd1f365dd1c4a5426202d13a8b106c7c7f6485260d",
        ),
        "reachability": (
            "98000a2cd58d36b292487e6180986500f835bebac64fe5799f5415f4bcaba3ad",
            "e5cb6465a48a04865b283bf4b9e5616144513ae57a81a5c0007408617764e696",
            "57feea9b49131a2d7ffe43becf30b9e42423f1c4ce40add596829f257bd66ee3",
        ),
        "forward": (
            "0e0e16399cddf0a9ee90536b975c725b4564284d692ea500836947d26a91332e",
            "c801e3a6101904b155ef6164cf8e295bd441b56f1849095829040df7a79fed3a",
            "a24ab78ba83459bd713dc6380fabe3c1b4427c6f3144656f8ffa52cef188c2b3",
        ),
    },
    "cube": {
        "acid": (
            "dade8d6afd8392f475d1e56c031f330c4e72c924e2c4254c2bcca5bf6d6be416",
            "03c00b01b2e9e038f3b553ee52288cb886432cc6e17f3c0e81e3ea49bb8b8830",
            "cc1c6a1bad9cc16d521a8e02f15d6a1d4ba423265e4c031801b1c086e12a468d",
        ),
        "reachability": (
            "ffc158daee855c4794e51ba48abbbc2045851db2c25080a4c4fe1a50673dd9b8",
            "548631decf704c8ca14375b5fffa9a4e302d4ec6406e7e2c7fa4ab6b304e86f9",
            "6e60966ea66f5518573d5eead7ae6a4da6f3c923939e4382e3f4aa21b2b4d8f3",
        ),
        "forward": (
            "1691fb0f6864dbad830a814cc98e54534a150da081299f40f3db77dea503ed62",
            "ae533413735dc59953272e5fe02b5da23f2b995ef11528ccc6727d256f7d5400",
            "db3285b38c469f139ed0879ac4cf4e9d8bfdea1540efd6c56f8de36627381aed",
        ),
    },
}


PROPOSAL_ARTIFACT_SHA256 = {
    "pusht": {
        "vp_true": (
            ("e1d605c2763877e8d2db0d5e66f052f778f4574ed6cffdbb3d0deaa832ed3f63", "2250884e8118c62e73ead61f3aa9b750fadd90cccc1c6a9ccfc4b7753afb0838"),
            ("aff467795b6c31edcb0855d699bafe3f9d77192eb1062da4d3bc95cd45dc7f3f", "9b1ac7dcc95b4f2ceb75e67de9b63497862a82cbe5349525c8c820d2dc78fefb"),
            ("4ab0ff1f38003e40a8e3db910688c8c7ff4cdb959f4322d2b4fbb5e2991a4b71", "4d96241539fe94f9780e75ab81175da6ced58090fa0314c6854a6f969321875a"),
        ),
        "vp_shuffled_goal": (
            ("757b2b061db87f222a12b1b5306d9bc750e146ae480fb229f83d78a0b71e927d", "af00d5fb888bc9660428dbc995be92d1f521ad95ff08ac5d9f134fcd349d703e"),
            ("908d37185d80f7d4fb26b600b1c7c9fb8b86692406a6326508e68129a8254468", "e51927898ac604f9f7bee19ebdb51b3805dc49d24d40f564d5e32e0daf3fe292"),
            ("fbd15b8b5eba3e32759928a3ebd8b4d09aafd99c8f4721083ce6a47ce5bbba17", "02c987edd52dafc48db59ecfce8ed324e5798a05953274e959590ccfc7d4028b"),
        ),
        "gaussian_true": (
            ("6e66a556c4f416c5e0f91b8c92dc6e8f63e324671386731b8fb09e417d9e4d0b", "c6e73b84d2b159dc1272df494563281561a64066f096853e5142fde9838b24ff"),
            ("28f6fceed3ba15fd309cde073e175b675cf8a91e13aff075ca87de8be085c9ed", "c7b89ebc553af60f3ad4a9d018906705a8eb524d42272434512ebc0be75f7e61"),
            ("08c7e9813a27486f4008d868f5d9a8fa4d40dfe6f783abc10b2ccba2ff6f6521", "868bbb1351d87106c5df770cfe405c13787db83abd13fe1dba20f655cf685f81"),
        ),
    },
    "reacher": {
        "vp_true": (
            ("ab80d4802bbab45cfd5c4cf6260538067e9fe3cc8b4e3f012bd1ecdd11378480", "6cbf6f365fdc2c6f612415203eba749689de21211fdc3274cb795515c35bcf3c"),
            ("c36f5d937119e313d71b28c6917cdc20d6a4a282e0a21f0588a1c82616b87e6e", "f3bff0cca69d51e4f9bb19dce91659d74d38d6af7c4dd6dd93f079d8da14f3dd"),
            ("6ad96ec1118773c76cd61763ebf399c5aec466c2609d326e49b2497a80a0591c", "91983713b67b397783d1328ede18a0a3c56631b072ca8081ce64f546118aaeda"),
        ),
        "vp_shuffled_goal": (
            ("a60480e9ff948aa65cb2d616ea8bcd41ad801f386e31b79ed93014c550099bf6", "2abca0590a3f620cf05d86d4d34287f05bc3f60bcb60b24362dcf1cbfcba18fb"),
            ("a187fdfee2cf8d76248b04c678f319e301c57fd23b1159ada4111aeefbc817ed", "7dfb3af063051cff317638dbd6bf85be155358a9c7dd741433435d05c090f38e"),
            ("90b9154b09afb9287fb7f77523081b74ca7552a899b3172d1e3b6a71ab019797", "78c441634a8d0845922894f086e707f017127a6cda56c3d6fd48981393d04fe8"),
        ),
        "gaussian_true": (
            ("3658a39257822345990f028afc920d2f1f6df9e3d8e15de412c32a5ce04b0474", "320187e4106db767fc57ea1fcc1e37eee1e767eea34f110623ef8903f1ba0b7a"),
            ("a1fa585ea1e3c55966c07af92ad5b838d1da0f019f8e4a1a43dd03fe9f14d999", "ad5f827e6b5f4ad5f27a29c4cc859447dd84750e0c640ccb8898861256f60615"),
            ("27e4e1e8179ec91d929e60d6d85122736cdfd4107c91be985f024bfcc436d0e1", "3222f5d36d4784bdacb96982bd0a5027ed46f10240f58623328bbe470b909fa7"),
        ),
    },
    "cube": {
        "vp_true": (
            ("13151d7aea908ff2dc08980180f6af92e24029f3515db0680cdf6fee1dc99326", "33cc2676640446d44b26946138b03724d2f2d24beb962c54e8dc3f4d0523dca2"),
            ("a0244111dd49c6f299dd36082b7de0217016b5d5c0f6647952682a77c16c2950", "9f6fbf9a332707e47d94eb1c7d24ce7b720d6095248d55ce9fb5825da0a59d87"),
            ("29127b35af48fa4946fca97923ce0e45af33bcfe07c0c9275d13326dd9a87950", "786fb621ebbded5f78c4c5f6d7ac68d9f12768a6ed45ced26163ae8cbbd41fbe"),
        ),
        "vp_shuffled_goal": (
            ("b4182ef59b0ec3d342eab75be1e056944c1c9fce3d982ed7c19b228d9c741800", "b699a1804653acae6de14d6c83abebfc4418358f3475f14a7e23a1dbd3694b9d"),
            ("1520a2595ca67b093ad266b9b7ddd8aab26ad0d559506f3f69a290f12d1233d9", "fa69607dfae7273b4b5f437a6a3eae318888668a0e66a4df5a711b0b0976c3ac"),
            ("4733c71c379d29586b017be7bfb40cf729152525c3f81572a619349110889c90", "d542d4f70de0974fd8198c404b7bce9db66531b04b00d2bf6aafb66c6f6ff437"),
        ),
        "gaussian_true": (
            ("08bbf65065e96f430fb0b23eff5b97813c74749b080a936b1f851b24648042d0", "3481fe922c93183943f84bd72a0c53ad8671db3e5f36792ee38d502920d3e3ab"),
            ("a32c64e1e9b346b61823ddb1e3c0076995353778cb17779b779ba6c9e17d2d73", "78cca44f684400f6e4bbc3fc9231067e77c119982e2c15562912f80c53278823"),
            ("dea809151ddb026b0486678e30aeacb73eb203e521db6430f379bdc799294bba", "3a86fd0cfea1270ab27261127c23e4ef608c74252bd5361b72b04be2307a70a9"),
        ),
    },
}


PLANNER_BASE_SEEDS = (8301, 8302, 8303)
VELOCITY_BASE_SEEDS = (9101, 9102, 9103)
GAUSSIAN_BASE_SEEDS = (9201, 9202, 9203)


def derived_seed(namespace: str, task: str, base_seed: int, shard: int) -> int:
    if namespace not in {"planner", "velocity", "gaussian"}:
        raise ValueError("invalid E11 seed namespace")
    if task not in TASKS or shard not in range(SHARD_COUNT):
        raise ValueError("invalid E11 task or shard")
    payload = f"gdp-e11|{namespace}|{task}|{base_seed}|{shard}".encode("utf-8")
    value = int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")
    return value % (2**63 - 1)


def seed_index(seed: int) -> int:
    try:
        return SEEDS.index(seed)
    except ValueError as error:
        raise ValueError(f"invalid E11 model seed {seed}") from error
