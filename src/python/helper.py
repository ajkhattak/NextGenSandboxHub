import os
import shutil

# called in driver.py
class colors:
    GREEN = '\033[92m'
    RED   = '\033[91m'
    END   = '\033[0m'

def create_clean_dirs(output_dir,
                      task_type,
                      clean = ["none"]):
    
    if (clean == ["all"]):
        subdirs  = os.listdir(output_dir)
        for d in subdirs:
            if (d != "data"):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
    elif (clean == ["existing"]):
        subdirs  = os.listdir(output_dir)
        for d in subdirs:
            if (d in ["configs", "outputs"]):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)
    elif (len(clean) >= 1 and clean != ["none"]):
        subdirs  = os.listdir(output_dir)
        for d in subdirs:
            if (d in clean):
                try:
                    shutil.rmtree(d)
                except:
                    os.remove(d)

   
    subdirs  = os.listdir(output_dir)

    for d in subdirs:
        if (d in ["configs", "outputs"]):
            try:
                shutil.rmtree(d)
            except:
                os.remove(d)

    os.mkdir("configs")
    if task_type == 'control':
        os.makedirs("outputs/div")
        os.makedirs("outputs/troute")
        #os.makedirs("outputs/troute_parq")
    
    if (os.path.isdir("dem")):
        shutil.rmtree("dem")
