"""Isolate Linux-only resource import so native artificial join tests can run."""
import ast,json
from .common import PKG,DOC,identity,write_new

def main():
    source=(PKG/'worker.py').read_text();old='import ast,hashlib,json,math,os,resource,sys,time,traceback'
    if source.count(old)!=1 or source.count('def main():\n')!=1:raise ValueError('exact original new-worker source')
    new=source.replace(old,'import ast,hashlib,json,math,os,sys,time,traceback').replace('def main():\n','def main():\n    import resource\n')
    ast.parse(new,feature_version=(3,6));write_new(PKG/'worker_v2.py',new.encode())
    tests=(PKG/'tests.py').read_text().replace('from .worker import process_parent','from .worker_v2 import process_parent').replace("DOC/'artificial-001'","DOC/'artificial-002'").replace("DOC/'ARTIFICIAL-001.json'","DOC/'ARTIFICIAL-002.json'")
    ast.parse(tests,feature_version=(3,6));write_new(PKG/'tests_v2.py',tests.encode())
    write_new(DOC/'ARTIFICIAL001-DISPOSITION.json',{'status':'NATIVE_TEST_IMPORT_FAILED_BEFORE_FIXTURES_LINUX_ONLY_RESOURCE_IMPORT_MOVED_TO_MAIN_IN_V2',
        'original_worker':identity(PKG/'worker.py'),'new_worker':identity(PKG/'worker_v2.py'),'original_test':identity(PKG/'tests.py'),'new_test':identity(PKG/'tests_v2.py'),
        'scientific_formulas_or_schema_changed':False,'live_saved_data_reads_or_jobs':0})
    print('Linux-only resource import isolated; original failed native test/source preserved')

if __name__=='__main__':main()
