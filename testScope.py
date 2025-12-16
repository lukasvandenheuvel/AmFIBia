from src.AquilosDriver import fibsem
import pickle

### INITIALIZE MICROSCOPE FROM DRIVER
scope=fibsem()
###



if __name__ == "__main__":

    img = scope.take_image_IB()
    out = {
        "img": img
    }

    with open('TEST.pickle', 'wb') as handle:
        pickle.dump(out, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print("Saved TEST.pickle")
