#### IMPORT MICROSCOPE
try:
    from autoscript_sdb_microscope_client import SdbMicroscopeClient
    from autoscript_sdb_microscope_client.enumerations import *
    from autoscript_sdb_microscope_client.structures import GrabFrameSettings, StagePosition
    # Set Up Microscope
    microscope = SdbMicroscopeClient()


    from autoscript_toolkit.template_matchers import * 
    import autoscript_toolkit.vision as vision_toolkit
    # from src.custom_matchers_v3 import *
except:
    print("No Autoscript installed")

import cv2
import numpy as np
import time
import os
import datetime

try:
    microscope.connect()
except:
    print("Couldn't connect to microscope, connecting to localhost")
    try:
        microscope.connect('localhost')
    except:
        print("Loading Testimages")



class fibsem:
    def __init__(self):
        '''
        Definition of directories and intrinsic handlers
        '''

        # History for milling actions
        self.history=[]

        # Output
        self.output_dir=''
        self.log_output = ''
        self.lamella_name=''

        # Default alignment current
        self.alignment_current = float(1e-11)

        try:
            microscope.specimen.stage.set_default_coordinate_system('Raw')
        except:
            print('no microscope connected')


    def get_available_ion_beam_currents(self):
        '''
        Get available ion beam currents from microscope
        '''
        return microscope.beams.ion_beam.beam_current.available_values
    
    def stop(self):
        '''
        Input: None
        Ouput: None
        Action: Stop operation by setting class variable "continuerun"
        '''
        self.continuerun = False

    def stop_patterning(self):
        '''
        Input: None
        Output: None
        Action: stop patterning if it is running
        '''
        if microscope.patterning.state=="Running":
            microscope.patterning.stop()

    def ion_on(self):
        if not microscope.beams.ion_beam.is_on:
            microscope.beams.ion_beam.turn_on()
        return()
    
    def electron_on(self):
        if not microscope.beams.electron_beam.is_on:
            microscope.beams.electron_beam.turn_on()
        return()
    
    def enter_sleep_mode(self):
        microscope.specimen.stage.home()
        microscope.beams.electron_beam.turn_off()
        microscope.beams.ion_beam.turn_off()
        return()
    
    def take_image_IB(self):
        '''
        Input: None
        Output: AdornedImage
        Action: Take IB image with standard parameters
        '''
        try:
            # Set view to electron beam
            microscope.imaging.set_active_view(2)

            #Check if EB is on, Turn on EB if not the case
            if microscope.beams.ion_beam.is_blanked:
                print("Ion beam blanked ")
                microscope.beams.ion_beam.turn_on()
            else:
                print("Ion beam turned on")
                
            # Aquire Snapshot in EB window
            print("Acquiring IB snapshot")
            framesettings = GrabFrameSettings(bit_depth=8)
            img = microscope.imaging.grab_frame(framesettings)
            return(img)
        except:
            print("ERROR: Could not take IB image")
        return()
    
    def take_image_EB(self):
        '''
        Input: None
        Output: Image as numpy array
        Action: Take EB image with standard parameters
        '''
        try:
            # Set view to electron beam
            microscope.imaging.set_active_view(1)

            #Check if EB is on, Turn on EB if not the case
            if microscope.beams.electron_beam.is_blanked:
                print("Ion beam blanked ")
            else:
                print("Electron beam turned on")
                microscope.beams.electron_beam.turn_on()

            # Aquire Snapshot in EB window
            print("Acquiring EB snapshot")
            img = microscope.imaging.grab_frame()

            return(img)
        except:
            print("ERROR: Could not take EB image")
        return()
    
    def get_stage_position(self):
        '''
        Input: None
        Output: current stageposition as directory
        Action: None
        '''

        #### Microscope dependent code ####
        try:
            stageposition=microscope.specimen.stage.current_position
        except:
            stageposition=StagePosition(x=0,y=0,z=0,r=0,t=0)
        x=stageposition.x
        y=stageposition.y
        z=stageposition.z
        r=stageposition.r
        t=stageposition.t
        

        #### Microscope independent code####
        stage_dict={'x':float(x),'y':float(y),'z':float(z),'r':float(r),'t':float(t)}
        return(stage_dict)
    
    def move_stage_absolute(self, stageposition):
        '''
        Input: Stage position as dictionnary
        Output: None
        Action: Move stage to provided stage position
        '''
        ### Microscope Independet Code ###
        x=float(stageposition['x'])
        y=float(stageposition['y'])
        z=float(stageposition['z'])
        r=float(stageposition['r'])
        t=float(stageposition['t'])
        #print(x,y,z,r,t)
        

        ### Microscope Dependent Code ###
        stagepos = StagePosition(x=x,y=y,z=z,t=t,r=r)
        microscope.specimen.stage.absolute_move(stagepos)
        return()
    

    def retreive_xT_patterns(self):
        '''
        Input: None
        Output: List of Patterns, each as AutoScript4 object
        Action: Retreives a list of currently drawn patterns from xT GUI
        '''
        # Read all patterns from the active view
        all_patterns = microscope.patterning.get_patterns()
        return(all_patterns)
    
    def auto_focus(self,beam="ELECTRON"):
        '''
        Input: Beam , currently only "ELECTRON" as autofocus in ION is damaging (also on a smaller sacrifice area...)
        Output: None
        Action: Autofocus function from the xT server
        '''
        active_view=microscope.imaging.get_active_view()
        if beam=="ELECTRON":
            microscope.imaging.set_active_view(1)
        else:
            microscope.imaging.set_active_view(2)
        microscope.auto_functions.run_auto_focus()
        microscope.imaging.set_active_view(active_view)
        return()
    
    def align(self,image,beam,current=1.0e-11):
        '''
        Input: Alignment image, Beam ("ION" or "ELECTRON"), optionally current but replaced by the GUI option
        Output: None
        Action: Align the stage and beam shift to the reference image at the current stage position
        '''
        current=self.alignment_current


        try:
            if beam=='ION':
                print('Running alignment')
                microscope.imaging.set_active_view(2)

                # Get old resolution of images to go back after alignment
                old_resolution=microscope.beams.ion_beam.scanning.resolution.value
                old_mag=microscope.beams.ion_beam.horizontal_field_width.value

                # Get resolution of reference image and set microscope to given HFW
                img_resolution=str(np.shape(image.data)[1])+'x'+str(np.shape(image.data)[0])
                microscope.beams.ion_beam.scanning.resolution.value=img_resolution
                microscope.beams.ion_beam.beam_current.value=current
                beam_current_string=str(microscope.beams.ion_beam.beam_current.value)


                # Get HFW from Image

                # Run auto contrast brightness and reset beam shift. Take an image as reference for alignment
                microscope.beams.ion_beam.horizontal_field_width.value=image.metadata.optics.scan_field_of_view.width
                #microscope.beams.ion_beam.horizontal_field_width.value =
                microscope.auto_functions.run_auto_cb()
                microscope.beams.ion_beam.beam_shift.value = Point(0,0)
                current_img = self.take_image_IB()


                # Load Matcher function and locate feature
                #favourite_matcher = CustomCVMatcher(cv2.TM_CCOEFF_NORMED, tiling=False)
                favourite_matcher = CustomCVMatcher('phase')
                l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                print("Current confidence: " + str(l.confidence))
                self.log_output=self.log_output+"Step Clarification: Initial Alignment after Stage move \n"
                self.log_output=self.log_output+"Current confidence: " + str(l.confidence)+'\n'


                # Start movements and log images
                move_count = 0

                now = datetime.datetime.now()
                current_img.save(self.output_dir + self.lamella_name+'_out/'+now.strftime("%Y-%m-%d_%H_%M_%S_")+self.lamella_name +'_'+ beam_current_string + '_first_move_'+str(move_count)+'.tif')
                self.log_output=self.log_output+"Saved Image as : "+self.output_dir + self.lamella_name+'_out/'+now.strftime("%Y-%m-%d_%H_%M_%S_")+self.lamella_name +'_'+ beam_current_string + '_first_move_'+str(move_count)+'.tif'+'\n'

                # If cross correlation metric too low, continue movements for maximum 3 steps
                while l.confidence < 0.98 and move_count < 3:
                    self.log_output = self.log_output + "Move Count =" + str(move_count) + '\n'
                    x = l.center_in_meters.x * -1 # sign may need to be flipped depending on matcher
                    y = l.center_in_meters.y * -1
                    distance = np.sqrt(x ** 2 + y ** 2)
                    print("Deviation (in meters): " + str(distance))
                    self.log_output = self.log_output + "Deviation (in meters): " + str(distance) + '\n'


                    # If distance, meaning offset between images low enough, stop.
                    if distance < 82.9e-06/3072/2:
                        break
                    elif distance > 1e-05:
                        # move stage and reset beam shift
                        print("Moving stage by ("+str(x)+","+str(y)+") and resetting beam shift...")
                        self.log_output = self.log_output + "Moving stage by ("+str(x)+","+str(y)+") and resetting beam shift... \n"
                        rotation=microscope.beams.ion_beam.scanning.rotation.value
                        print(rotation)
                        possible_rotations=[0,3.14]
                        #print(min(possible_rotations, key=lambda x: abs(x - rotation)))

                        if rotation==0:

                            pos_corr = StagePosition(coordinate_system='Specimen', x=-x, y=-y)

                            print('Rotation is zero')
                        else:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                            print('Rotation is NOT zero')
                        microscope.specimen.stage.relative_move(pos_corr)
                        microscope.beams.ion_beam.beam_shift.value = Point(0,0)

                    else:
                        # apply (additional) beam shift
                        print("Shifting beam by ("+str(x)+","+str(y)+")...")
                        self.log_output = self.log_output + "Shifting beam by ("+str(x)+","+str(y)+")... \n"
                        print(microscope.beams.ion_beam.beam_shift.value)
                        microscope.beams.ion_beam.beam_shift.value += Point(x,y) # incremental

                    move_count += 1

                    current_img = self.take_image_IB()
                    now = datetime.datetime.now()
                    current_img.save(self.output_dir+ self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_") + self.lamella_name +'_'+ beam_current_string + '_first_move_' + str(move_count)+'.tif')

                    self.log_output = self.log_output + "Saved Image as : " +self.output_dir+ self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_") + self.lamella_name +'_'+ beam_current_string + '_first_move_' + str(move_count)+'.tif'+'\n'
                    l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                    print("Current confidence: " + str(l.confidence))
                    self.log_output = self.log_output + "Current confidence: " + str(l.confidence) + '\n'

                # Go back to old resolution
                microscope.beams.ion_beam.scanning.resolution.value = old_resolution
                microscope.beams.ion_beam.horizontal_field_width.value = old_mag

                self.alignment_img_buffer = current_img
                print("Done.")



            if beam=="ELECTRON":
                # Same as above, just for alignment in SEM imaging
                print('Running alignment')
                microscope.imaging.set_active_view(1)
                old_resolution = microscope.beams.electron_beam.scanning.resolution.value
                old_mag = microscope.beams.electron_beam.horizontal_field_width.value

                img_resolution = str(np.shape(image.data)[1]) + 'x' + str(np.shape(image.data)[0])
                microscope.beams.electron_beam.scanning.resolution.value = img_resolution
                microscope.beams.electron_beam.horizontal_field_width.value = image.metadata.optics.scan_field_of_view.width
                microscope.beams.electron_beam.beam_shift.value = Point(0, 0)

                current_img = self.take_image_EB()


                favourite_matcher = CustomCVMatcher(cv2.TM_CCOEFF_NORMED, tiling=False)
                l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                print("Current confidence: " + str(l.confidence))
                move_count = 0

                while l.confidence < 0.98 and move_count < 1:
                    x = l.center_in_meters.x * -1  # sign may need to be flipped depending on matcher
                    y = l.center_in_meters.y * -1
                    distance = np.sqrt(x ** 2 + y ** 2)
                    print("Deviation (in meters): " + str(distance))


                    if distance > 1e-05:
                        # move stage and reset beam shift
                        print("Moving stage by ("+str(x)+","+str(y)+") and resetting beam shift...")
                        #self.log_output = self.log_output + "Moving stage by ("+str(x)+","+str(y)+") and resetting beam shift... \n"

                        rotation = microscope.beams.electron_beam.scanning.rotation.value
                        possible_rotations = [0, 3.14]
                        num=min(possible_rotations, key=lambda x: abs(x - rotation))
                        print(num)
                        if num==0:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=-x, y=-y)
                        else:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                        #pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                        microscope.specimen.stage.relative_move(pos_corr)
                        microscope.beams.electron_beam.beam_shift.value = Point(0,0)

                    else:
                        # apply (additional) beam shift
                        print("Shifting beam by ("+str(x)+","+str(y)+")")
                        #self.log_output = self.log_output + "Shifting beam by ("+str(x)+","+str(y)+")... \n"
                        print(microscope.beams.electron_beam.beam_shift.value)
                        microscope.beams.electron_beam.beam_shift.value += Point(x,y) # incremental

                    move_count += 1
                    current_img = self.take_image_EB()
                    l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                microscope.beams.electron_beam.scanning.resolution.value = old_resolution
                microscope.beams.electron_beam.horizontal_field_width.value = old_mag
                #self.alignment_img_buffer = current_img

        except:
            if beam == 'ION':
                print('Running alignment')
                microscope.imaging.set_active_view(2)
                old_resolution = microscope.beams.ion_beam.scanning.resolution.value
                old_mag = microscope.beams.ion_beam.horizontal_field_width.value

                # microscope.beams.ion_beam.scanning.resolution.value='768x512'
                img_resolution = str(np.shape(image.data)[1]) + 'x' + str(np.shape(image.data)[0])
                microscope.beams.ion_beam.scanning.resolution.value = img_resolution
                microscope.beams.ion_beam.beam_current.value = current

                # Get HFW from Image

                microscope.beams.ion_beam.horizontal_field_width.value = image.metadata.optics.scan_field_of_view.width
                microscope.auto_functions.run_auto_cb()
                microscope.beams.ion_beam.beam_shift.value = Point(0, 0)
                current_img = self.take_image_IB()


                #favourite_matcher = CustomCVMatcher(cv2.TM_CCOEFF_NORMED, tiling=False)
                favourite_matcher = CustomCVMatcher('phase')
                l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                print("Current confidence: " + str(l.confidence))

                self.log_output = self.log_output + "Step Clarification: Initial Alignment after Stage move \n"
                self.log_output = self.log_output + "Current confidence: " + str(l.confidence) + '\n'

                move_count = 0

                while l.confidence < 0.98 and move_count < 3:
                    self.log_output = self.log_output + "Move Count =" + str(move_count) + '\n'
                    x = l.center_in_meters.x * -1  # sign may need to be flipped depending on matcher
                    y = l.center_in_meters.y * -1
                    distance = np.sqrt(x ** 2 + y ** 2)
                    print("Deviation (in meters): " + str(distance))
                    self.log_output = self.log_output + "Deviation (in meters): " + str(distance) + '\n'

                    if distance < 82.9e-06 / 3072 / 2:
                        break
                    elif distance > 1e-05:
                        # move stage and reset beam shift
                        print("Moving stage by (" + str(x) + "," + str(y) + ") and resetting beam shift...")
                        self.log_output = self.log_output + "Moving stage by (" + str(x) + "," + str(
                            y) + ") and resetting beam shift... \n"
                        #pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)

                        rotation = microscope.beams.ion_beam.scanning.rotation.value
                        print(rotation)
                        possible_rotations = [0, 3.14]
                        #pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                        if rotation==0:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=-x, y=-y)
                            print('Rotation is zero')
                        else:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                            print('Rotation is NOT zero')
                        microscope.specimen.stage.relative_move(pos_corr)
                        microscope.beams.ion_beam.beam_shift.value = Point(0, 0)

                    else:
                        # apply (additional) beam shift
                        print("Shifting beam by (" + str(x) + "," + str(y) + ")...")
                        self.log_output = self.log_output + "Shifting beam by (" + str(x) + "," + str(y) + ")... \n"
                        print(microscope.beams.ion_beam.beam_shift.value)
                        microscope.beams.ion_beam.beam_shift.value += Point(x, y)  # incremental

                    move_count += 1

                    current_img = self.take_image_IB()
                    l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                    print("Current confidence: " + str(l.confidence))
                    self.log_output = self.log_output + "Current confidence: " + str(l.confidence) + '\n'
                microscope.beams.ion_beam.scanning.resolution.value = old_resolution
                microscope.beams.ion_beam.horizontal_field_width.value = old_mag

                print("Done.")

            if beam=="ELECTRON":
                #print("Not implemented yet")
                print('Running alignment')
                microscope.imaging.set_active_view(1)
                old_resolution = microscope.beams.electron_beam.scanning.resolution.value
                old_mag = microscope.beams.electron_beam.horizontal_field_width.value

                img_resolution = str(np.shape(image.data)[1]) + 'x' + str(np.shape(image.data)[0])
                microscope.beams.electron_beam.scanning.resolution.value = img_resolution
                microscope.beams.electron_beam.horizontal_field_width.value = image.metadata.optics.scan_field_of_view.width
                microscope.beams.electron_beam.beam_shift.value = Point(0, 0)

                current_img = self.take_image_EB()

                favourite_matcher = CustomCVMatcher(cv2.TM_CCOEFF_NORMED, tiling=False)
                l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                print("Current confidence: " + str(l.confidence))
                move_count = 0

                while l.confidence < 0.98 and move_count < 1:
                    x = l.center_in_meters.x * -1  # sign may need to be flipped depending on matcher
                    y = l.center_in_meters.y * -1
                    distance = np.sqrt(x ** 2 + y ** 2)
                    print("Deviation (in meters): " + str(distance))


                    if distance > 1e-05:
                        # move stage and reset beam shift
                        print("Moving stage by ("+str(x)+","+str(y)+") and resetting beam shift...")
                        #self.log_output = self.log_output + "Moving stage by ("+str(x)+","+str(y)+") and resetting beam shift... \n"
                        #pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                        if num==0:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=-x, y=-y)
                        if num==3.14:
                            pos_corr = StagePosition(coordinate_system='Specimen', x=x, y=y)
                        microscope.specimen.stage.relative_move(pos_corr)
                        microscope.beams.electron_beam.beam_shift.value = Point(0,0)

                    else:
                        # apply (additional) beam shift
                        print("Shifting beam by ("+str(x)+","+str(y)+")...")
                        #self.log_output = self.log_output + "Shifting beam by ("+str(x)+","+str(y)+")... \n"
                        print(microscope.beams.electron_beam.beam_shift.value)
                        microscope.beams.electron_beam.beam_shift.value += Point(x,y) # incremental
                        if num==0:
                            microscope.beams.electron_beam.beam_shift.value += Point(-x, -y)  # incremental
                        if num==3.14:
                            microscope.beams.electron_beam.beam_shift.value += Point(x, y)  # incremental

                    move_count += 1
                    current_img = self.take_image_EB()
                    l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                microscope.beams.electron_beam.scanning.resolution.value = old_resolution
                microscope.beams.electron_beam.horizontal_field_width.value = old_mag

        return()

    def align_current(self,new_current,beam='ION'):
        '''
        Input: Current to change towards, beam (currently "ION" only)
        Output: None
        Action: Take a reference image at the old current, change current and align to that reference image
        '''
        if beam=="ION":
            microscope.imaging.set_active_view(2)
            #pos1=microscope.specimen.stage.current_position
            microscope.auto_functions.run_auto_cb()
            beam_current_string = str(microscope.beams.ion_beam.beam_current.value)
            ref_img=self.take_image_IB()
            now = datetime.datetime.now()
            try:
                ref_img.save(self.output_dir + self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_")+ self.lamella_name + '_' + beam_current_string + '_align_current_refimg' + '.tif')
                self.log_output=self.log_output+"Saved Image as : " + self.output_dir + self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_")+ self.lamella_name + '_' + beam_current_string + '_align_current_refimg' + '.tif'+'\n'
            except:
                print("Run in Scripting Mode")
            microscope.beams.ion_beam.beam_current.value = new_current
            microscope.beams.ion_beam.scanning.dwell_time.value=200e-09
            microscope.beams.ion_beam.scanning.resolution.value = '768x512'
            microscope.auto_functions.run_auto_cb()
            current_img=microscope.imaging.grab_frame()


            move_count = 0
            now = datetime.datetime.now()
            try:
                current_img.save(self.output_dir + self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_")+ self.lamella_name  + '_'+ beam_current_string +  '_align_current_' + str(move_count)+'.tif')
                self.log_output = self.log_output + "Saved Image as : " + self.output_dir + self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_")+ self.lamella_name  + '_'+ beam_current_string +  '_align_current_' + str(move_count)+'.tif'+'\n'
            except:
                pass

            favourite_matcher = CustomCVMatcher(cv2.TM_CCOEFF_NORMED, tiling=False)
            l = vision_toolkit.locate_feature(current_img, ref_img, favourite_matcher)
            
            print("Current confidence: " + str(l.confidence))

            self.log_output = self.log_output + "Step Clarification: Current Alignment \n"
            self.log_output = self.log_output + "Current confidence: " + str(l.confidence) + '\n'


            while l.confidence < 0.999 and move_count < 3:
                self.log_output = self.log_output + "Move Count =" +str(move_count) +'\n'
                x = l.center_in_meters.x * -1
                y = l.center_in_meters.y * -1
                distance = np.sqrt(x ** 2 + y ** 2)

                
                print("Deviation (in meters): " + str(distance))
                self.log_output = self.log_output + "Deviation (in meters): " + str(distance) + '\n'
                if distance < 82.9e-06/768/2:
                    break
                elif distance < 1e-05:
                    print("Shifting beam by ("+str(x)+","+str(y)+")...")
                    self.log_output = self.log_output + "Shifting beam by (" + str(x) + "," + str(y) + ")... \n"
                    microscope.beams.ion_beam.beam_shift.value += Point(x,y)
                    move_count += 1
                    current_img = self.take_image_IB()
                    now = datetime.datetime.now()
                    try:
                        current_img.save(self.output_dir + self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_")+ self.lamella_name + '_'+ beam_current_string + '_align_current_' + str(move_count)+'.tif')
                        self.log_output = self.log_output + "Saved Image as : " + self.output_dir + self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_")+ self.lamella_name + '_'+ beam_current_string + '_align_current_' + str(move_count)+'.tif'+'\n'
                    except:
                        pass
                    l = vision_toolkit.locate_feature(current_img, ref_img, favourite_matcher)
                    print("Current confidence: " + str(l.confidence))
                    self.log_output = self.log_output + "Current confidence: " + str(l.confidence) + '\n'
                else:
                    print("Distance is greater than 10 microns. Abort.")
                    self.log_output = self.log_output + "Distance is greater than 10 microns. Abort.\n"
                    break
            microscope.auto_functions.run_auto_cb()



        return()