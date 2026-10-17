"""Preserved final publisher with only the presentation receipt selector changed."""
from .common import PKG,identity
from .freeze import payload

def main():
    files=payload();original=files['wm_diag1_saved_v1/final_publish.py'].decode('utf8')
    old="DOC/'REPORT-RECEIPT.json'";new="DOC/'REPORT-FORMAT-RECEIPT.json'"
    if original.count(old)!=1:raise ValueError('exact original frozen publisher receipt selector')
    namespace={'__name__':'wm_diag1_saved_v1.final_publish_preserved','__package__':'wm_diag1_saved_v1'}
    exec(compile(original.replace(old,new),'<frozen-publisher-presentation-receipt-only>','exec'),namespace)
    namespace['main']()

if __name__=='__main__':main()
