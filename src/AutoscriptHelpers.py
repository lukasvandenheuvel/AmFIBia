#### IMPORT MICROSCOPE
try:
    from autoscript_sdb_microscope_client import SdbMicroscopeClient
    from autoscript_sdb_microscope_client.enumerations import PatterningState
    from autoscript_sdb_microscope_client.structures import GrabFrameSettings, StagePosition, Rectangle, Point
    # Set Up Microscope
    microscope = SdbMicroscopeClient()


    from autoscript_toolkit.template_matchers import * 
    import autoscript_toolkit.vision as vision_toolkit
    from src.CustomMatchers import CustomCVMatcher
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
    
    def take_image_IB(self, reduced_area=None):
        '''
        Input: None
        Output: AdornedImage
        Action: Take IB image with standard parameters
        '''
        try:
            # Set view to electron beam
            microscope.imaging.set_active_view(2)

            #Check if IB is on, Turn on IB if not the case
            if microscope.beams.ion_beam.is_blanked:
                print("Ion beam blanked ")
                microscope.beams.ion_beam.turn_on()
            else:
                print("Ion beam turned on")
                
            # Aquire Snapshot in EB window
            print("Acquiring IB snapshot")
            if reduced_area is not None:
                reduced_area_rect = Rectangle(reduced_area['left'], reduced_area['top'], reduced_area['width'], reduced_area['height']) # 
                framesettings = GrabFrameSettings(bit_depth=8, reduced_area=reduced_area_rect)
            else:
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
        success = True
        try:
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

        except Exception as e:
            print(f"An error occurred while moving the stage: {e}")
            success = False

        return success
    

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
    
    def change_ion_beam_current(self,new_current):
        '''
        Input: New current as float
        Output: None
        Action: Change ion beam current to new current
        '''
        try:
            microscope.beams.ion_beam.beam_current.value = new_current
        except Exception as e:
            print(f"An error occurred while changing ion beam current: {e}")
            return False
        return True
    
    def align(self,image,current=1.0e-11,reduced_area=None, reset_beam_shift=True):
        '''
        Input: Alignment image, Beam ("ION" or "ELECTRON"), optionally current but replaced by the GUI option
        Output: None
        Action: Align the stage and beam shift to the reference image at the current stage position
        '''
        # current=self.alignment_current

        try:
            print('Running alignment')
            microscope.imaging.set_active_view(2)

            # Get old resolution of images to go back after alignment
            old_resolution = microscope.beams.ion_beam.scanning.resolution.value
            old_mag = microscope.beams.ion_beam.horizontal_field_width.value

            # Get resolution of reference image and set microscope to given HFW
            img_resolution = image.metadata.scan_settings.scan_size
            microscope.beams.ion_beam.scanning.resolution.value = img_resolution
            microscope.beams.ion_beam.beam_current.value = current
            beam_current_string = str(microscope.beams.ion_beam.beam_current.value)

            # Get HFW from Image

            # Run auto contrast brightness and reset beam shift. Take an image as reference for alignment
            microscope.beams.ion_beam.horizontal_field_width.value = image.metadata.optics.scan_field_of_view.width
            if reduced_area is not None: # Set reduced area if provided
                microscope.beams.ion_beam.scanning.mode.set_reduced_area(reduced_area["left"], reduced_area["top"], reduced_area["width"], reduced_area["height"])
            if reset_beam_shift:
                microscope.beams.ion_beam.beam_shift.value = Point(0,0)
            microscope.auto_functions.run_auto_cb()
            current_img = self.take_image_IB(reduced_area=reduced_area)

            # If image and template sizes differ, throw an error
            if current_img.width != image.data.shape[1] or current_img.height != image.data.shape[0]:
                print("ERROR: Image and template sizes differ. Cannot align.")
                return False

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
                    print(f"rotation: {rotation}")
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

                current_img = self.take_image_IB(reduced_area=reduced_area)
                now = datetime.datetime.now()
                current_img.save(self.output_dir+ self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_") + self.lamella_name +'_'+ beam_current_string + '_first_move_' + str(move_count)+'.tif')

                self.log_output = self.log_output + "Saved Image as : " +self.output_dir+ self.lamella_name + '_out/' +now.strftime("%Y-%m-%d_%H_%M_%S_") + self.lamella_name +'_'+ beam_current_string + '_first_move_' + str(move_count)+'.tif'+'\n'
                l = vision_toolkit.locate_feature(current_img, image, favourite_matcher)
                print("Current confidence: " + str(l.confidence))
                self.log_output = self.log_output + "Current confidence: " + str(l.confidence) + '\n'

            # Go back to old resolution
            microscope.beams.ion_beam.scanning.resolution.value = old_resolution
            microscope.beams.ion_beam.horizontal_field_width.value = old_mag
            if reduced_area is not None: # Get rid of the reduced area if it was provided
                microscope.beams.ion_beam.scanning.mode.set_full_frame()

            print("Done.")

        except Exception as e:
            print(f"An error occurred during alignment: {e}")
            return False

        return True

    def align_current(self,new_current):
        '''
        Input: Current to change towards
        Output: None
        Action: Take a reference image at the old current, change current and align to that reference image
        '''
        raise NotImplementedError("This function is not yet implemented.")
    
    def do_milling(self, pattern_dict):
        '''
        Input: 
            pattern_dict: Dictionary mapping pattern IDs to DisplayablePattern objects.
                          Each DisplayablePattern contains a .pattern attribute which is
                          one of: RectanglePattern, LinePattern, PolygonPattern, CirclePattern,
                          RegularCrossSectionPattern, CleaningCrossSectionPattern, StreamPattern, BitmapPattern
            milling_current: Milling current in Amperes
        Output: None
        Action: Creates patterns on the microscope and mills them
        '''
        try:
            # Clear any existing patterns
            microscope.patterning.clear_patterns()
            
            # Create each pattern on the microscope
            for pattern_id, displayable_pattern in pattern_dict.items():
                pattern = displayable_pattern.pattern
                xT_pattern = self._create_xT_pattern(pattern)
                
                if xT_pattern is None:
                    print(f"Warning: Unknown pattern type {type(pattern).__name__}, skipping pattern {pattern_id}")

            # Start the patterning job asynchronously
            microscope.patterning.start()

            # Continuously monitor the chamber pressure while the patterning job is active
            while microscope.patterning.state == PatterningState.RUNNING:
                pressure = microscope.vacuum.chamber_pressure.value
                time.sleep(1)

        except Exception as e:
            print(f"An error occurred during milling: {e}")
            return False
        
        return True
    
    def _create_xT_pattern(self, pattern, mode="scope"):
        '''
        Create an AutoScript pattern object from a CustomPatterns pattern.
        
        Input:
            pattern: A CustomPatterns pattern object (RectanglePattern, LinePattern, etc.)
        Output:
            xT_pattern: The created AutoScript pattern object, or None if pattern type is unknown
        '''
        if mode != "scope":
            from src.CustomPatterns import (
                RectanglePattern, LinePattern, PolygonPattern, CirclePattern,
                RegularCrossSectionPattern, CleaningCrossSectionPattern, 
                StreamPattern, BitmapPattern
            )
        else:
            from autoscript_sdb_microscope_client.structures import (
                RectanglePattern, LinePattern, PolygonPattern, CirclePattern,
                RegularCrossSectionPattern, CleaningCrossSectionPattern, 
                StreamPattern, BitmapPattern
            )
        
        xT_pattern = None
        
        if isinstance(pattern, RectanglePattern):
            xT_pattern = microscope.patterning.create_rectangle(
                center_x=pattern.center_x,
                center_y=pattern.center_y,
                width=pattern.width,
                height=pattern.height,
                depth=pattern.depth
            )
            # Set rectangle-specific properties
            xT_pattern.overlap_x = pattern.overlap_x
            xT_pattern.overlap_y = pattern.overlap_y
            if pattern.pitch_x > 0:
                xT_pattern.pitch_x = pattern.pitch_x
            if pattern.pitch_y > 0:
                xT_pattern.pitch_y = pattern.pitch_y
                
        elif isinstance(pattern, LinePattern):
            xT_pattern = microscope.patterning.create_line(
                start_x=pattern.start_x,
                start_y=pattern.start_y,
                end_x=pattern.end_x,
                end_y=pattern.end_y,
                depth=pattern.depth
            )
            # Set line-specific properties
            xT_pattern.overlap = pattern.overlap
            if pattern.pitch > 0:
                xT_pattern.pitch = pattern.pitch
                
        elif isinstance(pattern, PolygonPattern):
            # Convert vertices to list of [x, y] pairs
            vertices = [[v[0], v[1]] for v in pattern.vertices]
            xT_pattern = microscope.patterning.create_polygon(
                vertices=vertices,
                depth=pattern.depth
            )
            # Set polygon-specific properties
            xT_pattern.overlap_x = pattern.overlap_x
            xT_pattern.overlap_y = pattern.overlap_y
            if pattern.pitch_x > 0:
                xT_pattern.pitch_x = pattern.pitch_x
            if pattern.pitch_y > 0:
                xT_pattern.pitch_y = pattern.pitch_y
                
        elif isinstance(pattern, CirclePattern):
            xT_pattern = microscope.patterning.create_circle(
                center_x=pattern.center_x,
                center_y=pattern.center_y,
                outer_diameter=pattern.outer_diameter,
                inner_diameter=pattern.inner_diameter,
                depth=pattern.depth
            )
            # Set circle-specific properties
            xT_pattern.overlap_r = pattern.overlap_r
            xT_pattern.overlap_t = pattern.overlap_t
            if pattern.pitch_r > 0:
                xT_pattern.pitch_r = pattern.pitch_r
            if pattern.pitch_t > 0:
                xT_pattern.pitch_t = pattern.pitch_t
                
        elif isinstance(pattern, RegularCrossSectionPattern):
            xT_pattern = microscope.patterning.create_regular_cross_section(
                center_x=pattern.center_x,
                center_y=pattern.center_y,
                width=pattern.width,
                height=pattern.height,
                depth=pattern.depth
            )
            # Set cross-section-specific properties
            xT_pattern.overlap_x = pattern.overlap_x
            xT_pattern.overlap_y = pattern.overlap_y
            if pattern.pitch_x > 0:
                xT_pattern.pitch_x = pattern.pitch_x
            if pattern.pitch_y > 0:
                xT_pattern.pitch_y = pattern.pitch_y
            xT_pattern.multi_scan_pass_count = pattern.multi_scan_pass_count
            xT_pattern.scan_method = pattern.scan_method
            xT_pattern.scan_ratio = pattern.scan_ratio
                
        elif isinstance(pattern, CleaningCrossSectionPattern):
            xT_pattern = microscope.patterning.create_cleaning_cross_section(
                center_x=pattern.center_x,
                center_y=pattern.center_y,
                width=pattern.width,
                height=pattern.height,
                depth=pattern.depth
            )
            # Set cleaning cross-section-specific properties
            xT_pattern.overlap_x = pattern.overlap_x
            xT_pattern.overlap_y = pattern.overlap_y
            if pattern.pitch_x > 0:
                xT_pattern.pitch_x = pattern.pitch_x
            if pattern.pitch_y > 0:
                xT_pattern.pitch_y = pattern.pitch_y
                
        elif isinstance(pattern, StreamPattern):
            xT_pattern = microscope.patterning.create_stream(
                center_x=pattern.center_x,
                center_y=pattern.center_y,
                stream_file_path=pattern.stream_file_path
            )
                
        elif isinstance(pattern, BitmapPattern):
            xT_pattern = microscope.patterning.create_bitmap(
                center_x=pattern.center_x,
                center_y=pattern.center_y,
                width=pattern.width,
                height=pattern.height,
                depth=pattern.depth
            )
            if pattern.bitmap_data is not None:
                xT_pattern.bitmap_data = pattern.bitmap_data
            xT_pattern.fix_aspect_ratio = pattern.fix_aspect_ratio
        
        # Set common properties if pattern was created
        if xT_pattern is not None:
            self._set_common_pattern_properties(xT_pattern, pattern)
        
        return xT_pattern
    
    def _set_common_pattern_properties(self, xT_pattern, pattern):
        '''
        Set common properties shared by all pattern types.
        
        Input:
            xT_pattern: The AutoScript pattern object
            pattern: The CustomPatterns BasePattern-derived object
        '''
        # Set common properties that most patterns share
        if pattern.application_file:
            xT_pattern.application_file = pattern.application_file
        if pattern.beam_type:
            xT_pattern.beam_type = pattern.beam_type
        if pattern.blur > 0:
            xT_pattern.blur = pattern.blur
        if pattern.defocus != 0:
            xT_pattern.defocus = pattern.defocus
        if pattern.dose > 0:
            xT_pattern.dose = pattern.dose
        if pattern.dwell_time > 0:
            xT_pattern.dwell_time = pattern.dwell_time
        xT_pattern.enabled = pattern.enabled
        if pattern.gas_type:
            xT_pattern.gas_type = pattern.gas_type
        if pattern.gas_flow > 0:
            xT_pattern.gas_flow = pattern.gas_flow
        if pattern.gas_needle_position:
            xT_pattern.gas_needle_position = pattern.gas_needle_position
        if pattern.interaction_diameter > 0:
            xT_pattern.interaction_diameter = pattern.interaction_diameter
        xT_pattern.is_exclusion_zone = pattern.is_exclusion_zone
        if pattern.pass_count > 0:
            xT_pattern.pass_count = pattern.pass_count
        if pattern.refresh_time > 0:
            xT_pattern.refresh_time = pattern.refresh_time
        if pattern.rotation != 0:
            xT_pattern.rotation = pattern.rotation
        if pattern.scan_direction:
            xT_pattern.scan_direction = pattern.scan_direction
        if pattern.scan_type:
            xT_pattern.scan_type = pattern.scan_type