import os
from PIL import Image
import shutil
from math import floor, sqrt
import tempfile

MAXSIZE = 100000
MINSIZE =  80000

def get_resize_factor_jpg(desired, actual, dimensions):
    ratio = (actual / desired)
    if ratio <= 115/100:
        factor = sqrt(ratio) + 1.05
    elif ratio <= 135/100:
        factor = sqrt(ratio) * 1.08
    elif ratio <= 160/100:
        factor = sqrt(ratio) * 1.12
    elif ratio <= 180/100:
        factor = sqrt(ratio) * 1.16
    elif ratio <= 250/100:
        factor = sqrt(ratio) * 1.20
    else:
        factor = sqrt(ratio) * 1.25

    return floor(dimensions[0] / factor), floor(dimensions[1] / factor)

def makeJpg(file):
    img = Image.open(file)
    original_size = os.path.getsize(file)
    log_string = str(round(original_size/1000, 2))
    output = tempfile.TemporaryFile()
    img.convert('L').save(output, format="JPEG",  optimize=True, quality=75)     #first pass
    size = output.tell()    #get the saved file size
    log_string = log_string + "\t" + str(round(size/1000, 2))
    pass_counter = 1
    w, h = img.width, img.height
    
    x = 0
    while size > MAXSIZE:          #applying successive passes
        output.close()
        output = tempfile.TemporaryFile()
        
        if pass_counter == 2:
            w, h = get_resize_factor_jpg(MAXSIZE, size, (img.width, img.height))
        
        if pass_counter > 2:
            x = x + 4/100
            w, h = floor(w * (1-x)), floor(h * (1-x))
        
        img.convert('L').resize((w, h)).save(output, format='JPEG', optimize=True, quality=65)

        size = output.tell()
        log_string = log_string + "\t" + str(round(size/1000, 2))
        pass_counter += 1
    
    print(log_string)
    output.seek(0)
    return output

# TIFF Processing

def get_resize_factor_tiff(desired, actual, dimensions):
    ratio = (actual / desired)
    if ratio <= 115/100:
        factor = sqrt(ratio) * 1.025
    else:
        factor = sqrt(ratio) * 1.025

    return floor(dimensions[0] / factor), floor(dimensions[1] / factor)

def makeTif(file):
    img = Image.open(file)
    original_size = os.path.getsize(file)
    log_string = str(round(original_size/1000, 2))
    output = tempfile.TemporaryFile()
    img.convert('1').save(output, format="TIFF",  optimize=True)     #first pass
    size = output.tell()    #get the saved file size
    log_string = log_string + "\t" + str(round(size/1000, 2))
    pass_counter = 1
    
    x = 0
    while size > MAXSIZE:          #applying successive passes
        output.close()
        output = tempfile.TemporaryFile()

        if pass_counter == 1:
            w, h = get_resize_factor_tiff(MAXSIZE, size, (img.width, img.height))
        
        if pass_counter > 1:
            x = x + 4/100
            w, h = floor(w * (1-x)), floor(h * (1-x))

        img.convert('1').resize((w, h)).save(output, format="TIFF",  optimize=True)
        size = output.tell()
        log_string = log_string + "\t" + str(round(size/1000, 2))
        pass_counter += 1
    
    print(log_string, pass_counter)
    output.seek(0)
    return output


# if __name__ == "__main__":
#     INPATH = r"/Users/gauravpawar/Dev/mms/media/mandate/images/mandate/2025/03/07"
#     for filename in os.listdir(INPATH):
#         if filename.startswith("."):
#             continue
#         image_path = os.path.join(INPATH, filename)
#         output_file = makeTif(image_path)
#         with open(filename + "-reduced.jpeg", mode="wb") as f:
#             f.write(output_file.read())
