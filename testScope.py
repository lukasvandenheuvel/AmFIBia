from src.AquilosDriver import fibsem
import pickle

### INITIALIZE MICROSCOPE FROM DRIVER
scope=fibsem()
###



if __name__ == "__main__":

    img = scope.take_image_IB()
    

    directory = ""
    filename = ""
    pattern = scope.pattern_parser(directory,filename)


    out = {
        "img": img,
        "pattern": pattern
    }
    with open('TEST.pickle', 'wb') as handle:
        pickle.dump(out, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print("Saved TEST.pickle")
