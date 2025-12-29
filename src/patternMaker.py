import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import traceback
import numpy as np
import os

class Application:
    def __init__(self, root):
        self.root = root
        self.root.title("PatternMaker")
        self.root.geometry("480x930")
        
        # Notebook (tabs)
        notebook = ttk.Notebook(root)
        notebook.pack(expand=True, fill="both")

        # TAB 1 – blockprep frame
        blockprep_frame = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(blockprep_frame, text="BlockPrep")   

        # TAB 2 – Lamella frame
        lamella_frame = tk.Frame(notebook, padx=20, pady=20)
        notebook.add(lamella_frame, text="Polishing")

        # Liftout title
        label2 = tk.Label(blockprep_frame, text="Block Preparation", font=("Arial", 24))
        label2.pack(pady=10)

        # Lamella title
        label = tk.Label(lamella_frame, text="Polishing Pattern", font=("Arial", 24))
        label.pack(pady=10)

        # ========= BLOCKPREP FRAME =========

        # ========= GROUP 1 =========
        block_label = tk.Label(blockprep_frame, text="Block parameters", 
                                font=("Arial", 14, "bold"))
        block_label.pack(pady=(10, 5))

        block_frame = tk.Frame(blockprep_frame)
        block_frame.pack(pady=5, fill="x")

        self.block_width_um = self.create_param_entry(block_frame, "Block width (μm):", default_value="40")
        self.block_height_um = self.create_param_entry(block_frame, "Block height (μm):", default_value="35")
        self.block_depth_um = self.create_param_entry(block_frame, "Block depth (μm):", default_value="30")

        # Dropdown label
        dropdown_label = tk.Label(block_frame, text="Liftout mode:", font=("Arial", 12), width=15, anchor="w")
        dropdown_label.pack(side="left")

        # Dropdown (Combobox) with 2 choices
        self.mode = tk.StringVar()
        self.dropdown_box = ttk.Combobox(
            block_frame,
            textvariable=self.mode,
            font=("Arial", 12),
            state="readonly",
            values=["TopDown", "Planar"]
        )
        self.dropdown_box.current(0)  # default = first item
        self.dropdown_box.pack(side="left", fill="x", expand=True)
        

        # ========= GROUP 2 =========
        innerouter_label = tk.Label(blockprep_frame, text="Outer & Inner pattern:", 
                                font=("Arial", 14, "bold"))
        innerouter_label.pack(pady=(10, 5))

        innerouter_frame = tk.Frame(blockprep_frame)
        innerouter_frame.pack(pady=5, fill="x")

        self.outer_pattern_size_um = self.create_param_entry(innerouter_frame, "Outer pattern size (μm):", default_value="10")
        self.outer_margin_um = self.create_param_entry(innerouter_frame, "Outer margin (μm):", default_value="5")
        self.inner_pattern_size_um = self.create_param_entry(innerouter_frame, "Inner pattern size (μm):", default_value="8")
        self.inner_margin_um = self.create_param_entry(innerouter_frame, "Inner margin (μm):", default_value="0.5")

        # ========= GROUP 3 =========
        current_label = tk.Label(blockprep_frame, text="Which milling currents?", 
                                font=("Arial", 14, "bold"))
        current_label.pack(pady=(10, 5))

        current_frame = tk.Frame(blockprep_frame)
        current_frame.pack(pady=5, fill="x")

        # 3 checkboxes in a single row
        self.do_65nA = tk.BooleanVar(value=True)
        self.do_50nA = tk.BooleanVar(value=True)
        self.do_15nA = tk.BooleanVar(value=True)

        chk1 = tk.Checkbutton(current_frame, text="65nA", variable=self.do_65nA, font=("Arial", 12))
        chk2 = tk.Checkbutton(current_frame, text="50nA", variable=self.do_50nA, font=("Arial", 12))
        chk3 = tk.Checkbutton(current_frame, text="15nA", variable=self.do_15nA, font=("Arial", 12))

        chk1.pack(side="left", padx=10)
        chk2.pack(side="left", padx=10)
        chk3.pack(side="left", padx=10)

        # ========= GROUP 4 =========
        extra_label = tk.Label(blockprep_frame, text="Extra parameters", 
                                font=("Arial", 14, "bold"))
        extra_label.pack(pady=(10, 5))

        extra_frame = tk.Frame(blockprep_frame)
        extra_frame.pack(pady=5, fill="x")

        self.milling_angle = self.create_param_entry(extra_frame, "Milling angle", default_value="10")
        self.pattern_overlap_X = self.create_param_entry(extra_frame, "Pattern overlap X (%):", default_value="100")
        self.pattern_overlap_Y = self.create_param_entry(extra_frame, "Pattern overlap Y (%):", default_value="100")
        self.bridge_width_um = self.create_param_entry(extra_frame, "Bridge thickness (μm)", default_value="15")
        self.needle_gap_width_um = self.create_param_entry(extra_frame, "Needle gap width (μm):", default_value="25")
        self.needle_gap_height_um = self.create_param_entry(extra_frame, "Needle gap height (μm):", default_value="65")
        self.prefix_blockprep = self.create_param_entry(extra_frame, "Output prefix:", default_value="pattern-blockprep")

        # Button to trigger file reading
        button = tk.Button(blockprep_frame, text="Create pattern file", command=self.create_blockprep_file, 
                           font=("Arial", 12), padx=20, pady=10)
        button.pack(pady=20)

        # Status label
        self.status_label = tk.Label(blockprep_frame, text="", font=("Arial", 10))
        self.status_label.pack(pady=10)

        # ------ END blockprep frame -----

        # ========= LAMELLA FRAME =========

        # ========= GROUP 1 =========
        group1_label = tk.Label(lamella_frame, text="Lamella parameters", 
                                font=("Arial", 14, "bold"))
        group1_label.pack(pady=(10, 5))

        group1_frame = tk.Frame(lamella_frame)
        group1_frame.pack(pady=5, fill="x")

        self.lamella_thickness_nm = self.create_param_entry(group1_frame, "Lamella thickness (nm):", default_value="200")
        self.pattern_width_um = self.create_param_entry(group1_frame, "Pattern width (μm):", default_value="20")
        self.pattern_height_nm = self.create_param_entry(group1_frame, "Pattern height (nm):", default_value="300")
        self.depth_um = self.create_param_entry(group1_frame, "Pattern depth / Z (μm):", default_value="3")

        # ========= GROUP 2 =========
        group2_label = tk.Label(lamella_frame, text="Advanced parameters", 
                                font=("Arial", 14, "bold"))
        group2_label.pack(pady=(20, 5))

        group2_frame = tk.Frame(lamella_frame)
        group2_frame.pack(pady=5, fill="x")

        self.radius = self.create_param_entry(group2_frame, "Radius [>=1, 1 = perfect circle]:", default_value="1.2")
        self.num_points = self.create_param_entry(group2_frame, "Number of points in arc:", default_value="10")
        self.prefix_lamella = self.create_param_entry(group2_frame, "Output prefix:", default_value="pattern-polish")

        # Button to trigger file reading
        button = tk.Button(lamella_frame, text="Create pattern file", command=self.create_pattern_file, 
                           font=("Arial", 12), padx=20, pady=10)
        button.pack(pady=20)

        # Status label
        self.status_label = tk.Label(lamella_frame, text="", font=("Arial", 10))
        self.status_label.pack(pady=10)

        # ----- END lamella frame -------

    def create_param_entry(self, parent, label_text, default_value=""):
        """Create a labeled entry field inside a given parent."""
        frame = tk.Frame(parent)
        frame.pack(pady=3, fill="x")

        label = tk.Label(frame, text=label_text, font=("Arial", 12), width=25, anchor="w")
        label.pack(side="left")

        entry = tk.Entry(frame, font=("Arial", 12))
        entry.pack(side="left", fill="x", expand=True)

        entry.insert(0, default_value) 
        return entry
    
    def get_blockprep_parameters(self):
        """Return all blockprep parameters."""
        param_dict = {
            'block_width':          float(self.block_width_um.get())*1e-6,
            'block_height':         float(self.block_height_um.get())*1e-6,
            'block_depth':          float(self.block_depth_um.get())*1e-6,
            'inner_pattern_size':   float(self.inner_pattern_size_um.get())*1e-6,
            'inner_margin':         float(self.inner_margin_um.get())*1e-6,
            'outer_pattern_size':   float(self.outer_pattern_size_um.get())*1e-6,
            'outer_margin':         float(self.outer_margin_um.get())*1e-6,
            'do_65nA':              bool(self.do_65nA.get()),
            'do_50nA':              bool(self.do_50nA.get()),
            'do_15nA':              bool(self.do_15nA.get()),
            'milling_angle':        float(self.milling_angle.get()),
            'pattern_overlap_X':    float(self.pattern_overlap_X.get())/100,
            'pattern_overlap_Y':    float(self.pattern_overlap_Y.get())/100,
            'bridge_width':         float(self.bridge_width_um.get())*1e-6,
            'needle_gap_width':     float(self.needle_gap_width_um.get())*1e-6,
            'needle_gap_height':    float(self.needle_gap_height_um.get())*1e-6,
            'needle_gap_overlap':   2*1e-6,  # Hard-coded parameter
            'trench_safety_margin': 25*1e-6, # Hard-coded parameter
            'mode':                 self.mode.get(),
            'prefix':               self.prefix_blockprep.get(),
        }
        return param_dict

    def get_lamella_parameters(self):
        """Return all lamella parameters."""
        param_dict = {
            'lamella_thickness':    float(self.lamella_thickness_nm.get())*1e-9,
            'pattern_width':        float(self.pattern_width_um.get())*1e-6,
            'pattern_height':       float(self.pattern_height_nm.get())*1e-9,
            'depth':                float(self.depth_um.get())*1e-6,
            'radius':               float(self.radius.get()),
            'num_points':           int(self.num_points.get()),
            'prefix':               self.prefix_lamella.get(),
        }
        return param_dict
    
    def read_reference_file(self,reference_path):
        try:
            with open(reference_path, 'r') as f:
                file = f.read()
        except FileNotFoundError as e:
            self.show_error_log(f"FileNotFoundError: {str(e)}")
        except Exception as e:
            self.show_error_log(f"Error: {str(e)}\n\n{traceback.format_exc()}")
        return file

    def create_blockprep_file(self):
        """Create blockprep file"""
        params = self.get_blockprep_parameters()
    
        print("Parameters entered:", params)
        
        # Read reference file and obtain properties of pre-defined patterns
        file = self.read_reference_file('reference-pattern-blockprep_DO_NOT_REMOVE.ptf')
        vertices_dict = {}
        properties_dict = {}
        rectangles = file.split('<PatternRectangle>')[1:]
        for i,rect in enumerate(rectangles): # split the file in rectangles
            centerX = float(rect.split('CenterX ')[1].split('</CenterX')[0].split('"r8">')[1])
            centerY = float(rect.split('CenterY ')[1].split('</CenterY')[0].split('"r8">')[1])
            w = float(rect.split('Width ')[1].split('</Width')[0].split('"r8">')[1])
            l = float(rect.split('Length ')[1].split('</Length')[0].split('"r8">')[1])
            vertices_dict[i] = rectangle_vertices(centerX,centerY,w,l)
            properties_dict[i] = (centerX,centerY,w,l)

        enable_patterns = {
            '65nA': [0,8],
            '50nA': [0,4,5,7,9,14,11,12,13],
            '15nA': [0,1,2,3,6,10]
        }

        # Obtain parameters
        block_width             = params['block_width']
        block_height            = params['block_height']
        block_depth             = params['block_depth']
        inner_margin            = params['inner_margin']
        outer_margin            = params['outer_margin']
        inner_pattern_size      = params['inner_pattern_size']
        outer_pattern_size      = params['outer_pattern_size']
        milling_angle           = params['milling_angle']
        pattern_overlap_X       = params['pattern_overlap_X']
        pattern_overlap_Y       = params['pattern_overlap_Y']
        bridge_width            = params['bridge_width']
        needle_gap_width        = params['needle_gap_width']
        needle_gap_height       = params['needle_gap_height']
        needle_gap_overlap      = params['needle_gap_overlap']
        trench_safety_margin    = params['trench_safety_margin']
        mode                    = params['mode']
        do_65nA                 = params['do_65nA']
        do_50nA                 = params['do_50nA']
        do_15nA                 = params['do_15nA']
        prefix                  = params['prefix']

        # Define trench height using THALES theorem (Jean's method)
        trench_height = block_depth / np.tan(np.deg2rad(milling_angle)) + trench_safety_margin

        new_verts = {}
        new_verts[0] = rectangle_vertices(properties_dict[0][0],properties_dict[0][1],block_width,block_height)

        new_verts[1] = np.array([
            [new_verts[0][1,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][1,1] - inner_margin],
            [new_verts[0][1,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][1,1] - inner_margin - inner_pattern_size],
            [new_verts[0][2,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][2,1] - inner_margin - inner_pattern_size],
            [new_verts[0][2,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][2,1] - inner_margin]
        ])
        new_verts[2] = np.array([
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, new_verts[0][0,1] + inner_margin + pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, properties_dict[0][1] + bridge_width/2],
            [new_verts[0][0,0] - inner_margin, properties_dict[0][1] + bridge_width/2],
            [new_verts[0][0,0] - inner_margin, new_verts[0][0,1] + inner_margin + pattern_overlap_Y*inner_pattern_size]
        ])
        new_verts[3] = np.array([
            [new_verts[0][3,0] + inner_margin, new_verts[0][3,1] + inner_margin + pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][3,0] + inner_margin, new_verts[0][2,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][3,0] + inner_margin + inner_pattern_size, new_verts[0][2,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][3,0] + inner_margin + inner_pattern_size, new_verts[0][3,1] + inner_margin + pattern_overlap_Y*inner_pattern_size]
        ])
        new_verts[4] = np.array([
            [new_verts[0][3,0] + outer_margin, new_verts[0][3,1] + outer_margin + pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin, new_verts[0][2,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][2,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][3,1] + outer_margin + pattern_overlap_Y*outer_pattern_size]
        ])
        new_verts[5] = np.array([
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin],
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin - outer_pattern_size],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin - outer_pattern_size],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][1,1] - outer_margin]
        ])
        new_verts[6] = np.array([
            [new_verts[0][0,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][0,1] + inner_margin + inner_pattern_size],
            [new_verts[0][0,0] - inner_margin - pattern_overlap_X*inner_pattern_size, new_verts[0][0,1] + inner_margin],
            [new_verts[0][3,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][3,1] + inner_margin],
            [new_verts[0][3,0] + inner_margin + pattern_overlap_X*inner_pattern_size, new_verts[0][3,1] + inner_margin + inner_pattern_size]
        ])
        new_verts[7] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, properties_dict[0][1] + bridge_width/2],
            [new_verts[0][0,0] - outer_margin, properties_dict[0][1] + bridge_width/2],
            [new_verts[0][0,0] - outer_margin, new_verts[0][0,1] + outer_margin + pattern_overlap_Y*outer_pattern_size]
        ])
        new_verts[8] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size + trench_height]
        ])
        new_verts[9] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, properties_dict[0][1] - bridge_width/2],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][1,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, new_verts[0][1,1] - outer_margin - pattern_overlap_Y*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, properties_dict[0][1] - bridge_width/2]
        ])
        new_verts[10] = np.array([
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, properties_dict[0][1] - bridge_width/2],
            [new_verts[0][0,0] - inner_margin - inner_pattern_size, new_verts[0][1,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][0,0] - inner_margin, new_verts[0][1,1] - inner_margin - pattern_overlap_Y*inner_pattern_size],
            [new_verts[0][0,0] - inner_margin, properties_dict[0][1] - bridge_width/2]
        ])
        new_verts[11] = np.array([
            [new_verts[0][3,0] + outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height],
            [new_verts[0][3,0] + outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height - needle_gap_overlap],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height - needle_gap_overlap],
            [new_verts[0][3,0] + outer_margin + outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height]
        ])
        new_verts[12] = np.array([
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height],
            [new_verts[0][0,0] - outer_margin - outer_pattern_size, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][0,0] - outer_margin, new_verts[0][0,1] + outer_margin + 0.5*outer_pattern_size + trench_height]
        ])
        new_verts[13] = np.array([
            [new_verts[0][3,0] + outer_margin, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height],
            [new_verts[0][3,0] + outer_margin, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + needle_gap_width, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size],
            [new_verts[0][3,0] + outer_margin + needle_gap_width, new_verts[0][3,1] + outer_margin + 0.5*outer_pattern_size + needle_gap_height]
        ])
        new_verts[14] = np.array([
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][0,1] + outer_margin + outer_pattern_size],
            [new_verts[0][1,0] - outer_margin - pattern_overlap_X*outer_pattern_size, new_verts[0][0,1] + outer_margin],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][3,1] + outer_margin],
            [new_verts[0][2,0] + outer_margin + pattern_overlap_X*outer_pattern_size, new_verts[0][3,1] + outer_margin + outer_pattern_size]
        ])

        if mode=='Planar':
            # Flip the X coordinates of the vertical patterns
            new_verts[2][:,0]  = new_verts[2][:,0] + 2*inner_margin + block_width + inner_pattern_size
            new_verts[10][:,0] = new_verts[10][:,0] + 2*inner_margin + block_width + inner_pattern_size
            new_verts[7][:,0]  = new_verts[7][:,0] + 2*outer_margin + block_width + outer_pattern_size
            new_verts[9][:,0]  = new_verts[9][:,0] + 2*outer_margin + block_width + outer_pattern_size
            new_verts[3][:,0]  = new_verts[3][:,0] - 2*inner_margin - block_width - inner_pattern_size
            new_verts[4][:,0]  = new_verts[4][:,0] - 2*outer_margin - block_width - outer_pattern_size
            # Pattern 11 is the same as pattern 12, flipped along X
            new_verts[11][:,1:3] = new_verts[12][:,1:3]

        # Define which patterns to write in output file, this depends on milling current
        milling_currents = []
        do_65nA and milling_currents.append('65nA')
        do_50nA and milling_currents.append('50nA')
        do_15nA and milling_currents.append('15nA')

        # Strings for output file
        width_str = self.block_width_um.get()
        height_str = self.block_height_um.get()
        depth_str = self.block_depth_um.get()

        # Write output file
        self.output_path = ""

        for current in milling_currents:
            out_string = file.split('  <PatternRectangle>')[0]
            for i,verts in new_verts.items():
                enable = 'True'
                if i==0: # The first pattern is the BLOCK: it should not be enabled!
                    enable = 'False'
                if i in enable_patterns[current]:
                    (centerX,centerY,w,l) = rectangle_properties(verts)
                    new_rect_string = rectangles[i].split('</PatternRectangle>')[0]
                    new_rect_string = change_pattern_value('CenterX',centerX,new_rect_string,type='r8')
                    new_rect_string = change_pattern_value('CenterY',centerY,new_rect_string,type='r8')
                    new_rect_string = change_pattern_value('Width',w,new_rect_string,type='r8')
                    new_rect_string = change_pattern_value('Length',l,new_rect_string,type='r8')
                    new_rect_string = change_pattern_value('Enable',enable,new_rect_string,type='string')
                    out_string = out_string + '  <PatternRectangle>' + new_rect_string + '</PatternRectangle>\n'

            out_string = out_string + '</Content>'
            output_name = f'{prefix}-{mode}-{current}-w{width_str}um-h{height_str}um-d{depth_str}um.ptf'
            with open(output_name,'w') as f:
                f.write(out_string)
            self.output_path = self.output_path + os.path.abspath(output_name) + "\n"

        self.show_success_window()
        
    def create_pattern_file(self):
        """Create pattern file"""
        params = self.get_lamella_parameters()
    
        print("Parameters entered:", params)
        file = self.read_reference_file('reference-pattern-polish_DO_NOT_REMOVE.ptf')

        # Define parameters
        pattern_height = params['pattern_height']
        pattern_width = params['pattern_width']
        lamella_thickness = params['lamella_thickness']
        num_points = params['num_points']
        radius = params['radius']
        depth = params['depth']
        prefix = params['prefix']
        
        # define top pattern
        x_coords,y_coords = define_arc(pattern_height,radius=radius,num_points=num_points)
        w = pattern_width / 2
        # right-hand side
        x_rhs = x_coords + w
        y_rhs = y_coords + lamella_thickness / 2
        # left-hand side
        x_lhs = -x_coords - w
        y_lhs = y_coords + lamella_thickness / 2
        x1 = np.concatenate([x_rhs,np.flipud(x_lhs)])
        y1 = np.concatenate([y_rhs,np.flipud(y_lhs)])

        # define bottom pattern
        x2 = x1
        y2 = -y1

        out_string = file.split('<PatternPolygon>')[0]
        # first polygon
        points_string_1 = define_points_string(x1,y1)
        polygon_string_1 = file.split('<PatternPolygon>')[1].split('&lt;Point&gt;')[0]
        out_string = out_string + '<PatternPolygon>' + change_pattern_depth(polygon_string_1,depth) + points_string_1 + '</Points>' + file.split('<PatternPolygon>')[1].split('&lt;Point&gt;')[-1].split('</Points>')[1]
        # second polygon
        points_string_2 = define_points_string(x2,y2)
        polygon_string_2 = file.split('<PatternPolygon>')[2].split('&lt;Point&gt;')[0]
        out_string = out_string + '<PatternPolygon>' + change_pattern_depth(polygon_string_2,depth) + points_string_2 + '</Points>' + file.split('<PatternPolygon>')[2].split('&lt;Point&gt;')[-1].split('</Points>')[1]

        thickness_str = self.lamella_thickness_nm.get()
        width_str = self.pattern_width_um.get()
        depth_str = self.depth_um.get()
        output_name = f'{prefix}-{thickness_str}nm-{width_str}um-{depth_str}um.ptf'
        with open(output_name,'w') as f:
            f.write(out_string)
        self.output_path = os.path.abspath(output_name)
        self.show_success_window()

    def show_success_window(self):
        success_window = tk.Toplevel(self.root)
        success_window.title("Success")
        success_window.geometry("300x150")

        msg = tk.Label(success_window, text=f"Succesfully created\n{self.output_path}",
                    font=("Arial", 12))
        msg.pack(pady=20)

        success_window.update_idletasks()
        width = msg.winfo_reqwidth() + 40
        height = msg.winfo_reqheight() + 80
        success_window.geometry(f"{width}x{height}")
        # ----------------------------------------------

        ok_button = tk.Button(success_window, text="OK",
                            font=("Arial", 12),
                            command=success_window.destroy)
        ok_button.pack(pady=10)

    def show_error_log(self, error_message):
        """Open a new window with error log"""
        log_window = tk.Toplevel(self.root)
        log_window.title("Error Log")
        log_window.geometry("600x400")

        error_label = tk.Label(log_window, text="An Error Occurred:",
                               font=("Arial", 14, "bold"), fg="red")
        error_label.pack(pady=10)

        log_text = scrolledtext.ScrolledText(log_window, width=70, height=20,
                                             font=("Courier", 10))
        log_text.pack(padx=10, pady=10, expand=True, fill='both')
        log_text.insert('1.0', error_message)
        log_text.config(state='disabled')

        close_button = tk.Button(log_window, text="Close",
                                 command=log_window.destroy,
                                 font=("Arial", 10))
        close_button.pack(pady=10)

def rectangle_vertices(centerX,centerY,w,l):
    # Returns an 4x2 array with the X,Y coordinates of the vertices that define a rectangle.
    # The points are anticlockwise. 
    rect_verts = np.zeros((4,2))
    rect_verts[0,:] = np.array([centerX - w/2, centerY + l/2])
    rect_verts[1,:] = np.array([centerX - w/2, centerY - l/2])
    rect_verts[2,:] = np.array([centerX + w/2, centerY - l/2])
    rect_verts[3,:] = np.array([centerX + w/2, centerY + l/2])
    return rect_verts

def rectangle_properties(vertices):
    # Returns (X,Y,w,l) of the rectangle defined by 4 vertices.
    w = (vertices[3,0] - vertices[0,0])
    l = (vertices[0,1] - vertices[1,1])
    centerX = vertices[1,0] + w/2
    centerY = vertices[1,1] + l/2
    assert w>0, "ERROR: width needs to be positive! Is your rectangle defined in the right order of vertices?"
    assert l>0, "ERROR: Length needs to be positive! Is your rectangle defined in the right order of vertices?"
    return (centerX,centerY,w,l)

def define_arc(pattern_height,radius=1.2,num_points=10):
    # Create two arrays of point coordinates (x_coords and y_coords) which define the sides of the lamella.
    h = pattern_height
    circle_radius = h * radius
    xT = np.sqrt(circle_radius**2 - (circle_radius-h)**2)
    theta0 = - np.pi / 2
    theta1 = np.arctan2( h-circle_radius, xT ) # arctan: y,x
    x_coords,y_coords = define_points_on_circle(0,circle_radius,circle_radius,theta0,theta1,num_points=num_points)
    return x_coords,y_coords

def define_points_on_circle(xM,yM,R,theta0,theta1,num_points=10):
    # Create two arrays of point coordinates (x_coords and y_coords) which define a part of a circle between theta0 and theta1.
    theta_min = np.min([theta0,theta1])
    theta_max = np.max([theta0,theta1])
    theta_array = np.linspace(theta_min,theta_max,num_points)
    x_coords = R * np.cos(theta_array) + xM
    y_coords = R * np.sin(theta_array) + yM
    return x_coords,y_coords

def define_points_string(x_array,y_array):
    points_string = ''
    for x,y in zip(x_array,y_array):
        points_string = points_string + '&lt;Point&gt;\n'
        points_string = points_string + '&lt;PositionX xmlns:dt="urn:schemas-microsoft-com:datatypes" dt:dt="r8"&gt;{:.14E}&lt;/PositionX&gt;\n\n'.format(x)
        points_string = points_string + '&lt;PositionY xmlns:dt="urn:schemas-microsoft-com:datatypes" dt:dt="r8"&gt;{:.14E}&lt;/PositionY&gt;\n'.format(y)
        points_string = points_string + '&lt;/Point&gt;\n\n'
    points_string = points_string + '&lt;/Points&gt;\n'
    return points_string

def change_pattern_depth(polygon_string,depth):
    depth_string = '<Depth xmlns:dt="urn:schemas-microsoft-com:datatypes" dt:dt="r8">{:.14E}</Depth>'.format(depth)
    return polygon_string.split('<Depth xmlns:')[0] + depth_string + polygon_string.split('</Depth>')[1]

def change_pattern_value(property,value,pattern_string,type='r8'):
    if type=='r8': # string
        string = '<PROP xmlns:dt="urn:schemas-microsoft-com:datatypes" dt:dt="{}">{:.14E}</PROP>'.format(type,value).replace('PROP',property)
    else:
        string = '<PROP xmlns:dt="urn:schemas-microsoft-com:datatypes" dt:dt="{}">{}</PROP>'.format(type,value).replace('PROP',property)
    return pattern_string.split('<'+property+' xmlns:')[0] + string + pattern_string.split('</'+property+'>')[1]

def main():
    root = tk.Tk()
    app = Application(root)
    root.mainloop()

if __name__ == "__main__":
    main()
