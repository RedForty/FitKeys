# Tool to fit selected keys to previous and next unselected key
'''
Install: 
Place this script in your USERNAME/Documents/maya/scripts folder

Usage (python script):
# begin
import fit_keys
fit_keys.ui()
# end


'''
# --------------------------------------------------------------------------- #
# Imports

from maya import cmds



# --------------------------------------------------------------------------- #
# Globals

SLIDER_VALUE = 0.85
SLIDER_SCALE = None
SLIDERS = []
KEY_DATA = {}
GRAPH_EDITOR = 'graphEditor1GraphEd'
SNAPSHOT = False

# --------------------------------------------------------------------------- #
# Helpers

# Thank you Freya Holmer | Neat Corp
# https://youtu.be/NzjF1pdlK7Y

def lerp(a, b, t):
    return ((1.0 - t) * a + b * t)
    
def inv_lerp(a, b, v):
    return ((v - a) / (b - a))

def remap(iMin, iMax, oMin, oMax, v):
    t = inv_lerp(iMin, iMax, v)
    return lerp(oMin, oMax, t)

def is_equal(lst):
    return not lst or lst.count(lst[0]) == len(lst)

# --------------------------------------------------------------------------- #
# The main show


def get_selected_keyframes():
    ''' Returns a dictionary where the keys are curve names and the values are 
        [times, values]
        ie, {'curve_name' : [times, values]}
    '''

    # get the key selection
    if not cmds.animCurveEditor(GRAPH_EDITOR, exists=True):
        cmds.error("{} not found.".format(GRAPH_EDITOR))
        return # Cannot find graph editor?

    if not cmds.animCurveEditor(GRAPH_EDITOR, q=True, areCurvesSelected=True):
        cmds.warning("Must select some keys to fit.")
        return
            
    selected_curves = cmds.keyframe(q=True, selected=True, name=True) or []
    if not selected_curves: return None # Bounce early

    # The Data dictionary
    key_data = {}
    
    for curve in selected_curves:

        selected_index = cmds.keyframe(curve, q=True, selected=True, indexValue=True)
        if len(selected_index) == 1: continue # Bounce 
        selected_times = cmds.keyframe(curve, q=True, selected=True)
        num_keys       = cmds.keyframe(curve, q=True, keyframeCount=True)
        
        # Now expand ranges to include pivots
        time_range = []
        index_range = []
        if min(selected_index) == 0:
            left_pivot_index = min(selected_index)
        else:
            left_pivot_index = min(selected_index) - 1
        index_range.append(left_pivot_index)
        left_pivot_time = cmds.keyframe(curve, q=True, index=(left_pivot_index, ))
        time_range.extend(left_pivot_time)
            
        time_range.extend(selected_times)
        index_range.extend(selected_index)
        
        if max(selected_index) == num_keys - 1:
            right_pivot_index = max(selected_index)
        else:
            right_pivot_index = max(selected_index) + 1
        index_range.append(right_pivot_index)
        right_pivot_time = cmds.keyframe(curve, q=True, index=(right_pivot_index, ))
        time_range.extend(right_pivot_time)
    
        # Now grab values
        if len(index_range) == len(set(index_range)): # Optimization to run one call if all index are unique
            value_range = cmds.keyframe(curve, q=True, index=(index_range[0], index_range[-1]), valueChange=True)
        else: # Old fashioned way
            value_range = []
            for index in index_range:
                value = cmds.keyframe(curve, q=True, index=(index, ), valueChange=True)
                value_range.extend(value)
        
        if is_equal(value_range): continue # Ignore flat curves

        key_data[curve] = [time_range, value_range]
    
    if key_data:
        return key_data
    else:
        return None
        

def skew(times, values, slider_value):
    ''' Will skew values inside the pivots (first and last value) to 
        match the first and last pivot.
    '''

    if slider_value >= 0:
        slider_positive = True
    else:
        slider_positive = False
    
    percentage = abs(slider_value)

    left_pivot = values[0] - values[1]
    right_pivot = values[-2] - values[-1]

    if slider_positive:
        left_pivot = 0.0
    else:
        right_pivot = 0.0

    new_values = [x + (left_pivot) for x in values] # Shift everything to match left pivot

    for index, value in enumerate(new_values):
        # print(value)
        if index == 0 or index == len(values) - 1:
            new_values[index] = value - left_pivot
            continue

        time_slope = 1 - (times[index] - times[1]) / (times[-2] - times[1])
        offset_value = value - (right_pivot + left_pivot)
        
        # Then skew everything to right pivot by scaling along time slope.
        new_value = ((value - offset_value) * time_slope) + offset_value
        
        new_values[index] = new_value

    lerped_values = [lerp(x, y, percentage) for x, y in zip(values, new_values)]

    return lerped_values


def fit_skew(times, values, slider_value):
    ''' Will skew values inside the pivots (first and last value) to 
        match the first and last pivot.
    '''

    left_pivot = values[0] - values[1] 
    right_pivot = values[-2] - values[-1] + left_pivot

    new_values = [x + (left_pivot) for x in values] # Shift everything to match left pivot

    for index, value in enumerate(new_values):
        if index == 0 or index == len(values) - 1: 
            new_values[index] = value - left_pivot
            continue

        time_slope = 1 - (times[index] - times[1]) / (times[-2] - times[1])

        offset_value = value - (right_pivot)
        
        # Then skew everything to right pivot by scaling along time slope.
        new_value = ((value - offset_value) * time_slope) + offset_value
        
        new_values[index] = new_value

    lerped_values = [lerp(x, y, slider_value) for x, y in zip(values, new_values)]
    
    return lerped_values


def fit_scale(times, values, slider_value):
    ''' Will scale values inside the pivots (first and last value) to 
        match the first and last pivot.
    '''    
    
    left_pivot = values[0] - values[1] 

    new_values = [x + (left_pivot) for x in values] # Shift everything to match left pivot
    post_delta_scale = (values[-1] - values[0]) / (new_values[-2] - values[0])
    
    for index, value in enumerate(new_values):
        if index == 0 or index == len(values) + 1: 
            new_values[index] = value - left_pivot
            continue
        
        # Scale set to fit
        new_value = ((value - values[0]) * post_delta_scale) + values[0]
        new_values[index] = new_value
        
    lerped_values = [lerp(x, y, slider_value) for x, y in zip(values, new_values)]

    return lerped_values


def apply_values(curve, times, values):
    # Do the magic, do the magic!
    for time, value in zip(times, values):
        cmds.keyframe(curve, e=True, time=(time,), valueChange=value)


def begin(left=False, right=False):
    global SNAPSHOT
    if not SNAPSHOT:
        global KEY_DATA
        KEY_DATA = get_selected_keyframes()
        if left:
            for curve, data in KEY_DATA.items():
                times, values = data
                times.append(times[-1]+1)
                values.append(values[-1])
                KEY_DATA[curve] = [times, values]
                
        if right:
            for curve, data in KEY_DATA.items():
                times, values = data
                times.insert(0, times[0]-1)
                values.insert(0, values[0])
                KEY_DATA[curve] = [times, values]
                
        SNAPSHOT = True
        cmds.undoInfo(openChunk=True)


def update_skew_either(*args):
    begin()
    slider_value = args[0]
    if KEY_DATA:
        for curve, data in KEY_DATA.items():
            times, values = data
            new_values = skew(times, values, slider_value)
            apply_values(curve, times[1:-1], new_values[1:-1])

def update_skew(*args):
    begin()
    slider_value = args[0]
    if KEY_DATA:
        for curve, data in KEY_DATA.items():
            times, values = data
            new_values = fit_skew(times, values, slider_value)
            apply_values(curve, times[1:-1], new_values[1:-1])


def update_scale(*args):
    begin()
    slider_value = args[0]
    if KEY_DATA:
        for curve, data in KEY_DATA.items():
            times, values = data
            if values[1] == values[-2]: continue
            new_values = fit_scale(times, values, slider_value)
            apply_values(curve, times[1:-1], new_values[1:-1])


def end():
    global SNAPSHOT
    global KEY_DATA
    SNAPSHOT = False
    KEY_DATA = None
    cmds.undoInfo(closeChunk=True)


def complete_skew(*args):
    end()
    for slider in SLIDERS:
        cmds.floatSliderGrp(slider, edit=True, value=0)


def complete_scale(*args):
    end()
    cmds.floatSliderGrp(SLIDER_SCALE, edit=True, value=0)


# def run(slider_value = None):
#     global KEY_DATA
#     if slider_value == None:
#         slider_value = SLIDER_VALUE
    
#     KEY_DATA = get_selected_keyframes()
#     if not SLIDER: 
#         update(slider_value)


def ui():
    global SLIDER_SCALE
    global SLIDERS
    
    window = cmds.window(title="Fit Keys", iconName='fitkeys', widthHeight=(500, 55))
    cmds.columnLayout( adjustableColumn=True )
    SLIDER_SCALE       = cmds.floatSliderGrp( label='Scale ', field=False, min=0.0, max=1.0, value=0.0, step=0.01, dragCommand=update_scale, changeCommand=complete_scale, adjustableColumn=2 )
    SLIDER_SKEW_BOTH   = cmds.floatSliderGrp( label='Skew Both' , field=False, min=0.0, max=1.0, value=0.0, step=0.01, dragCommand=update_skew,  changeCommand=complete_skew, adjustableColumn=2  )
    SLIDER_SKEW_EITHER = cmds.floatSliderGrp( label='Skew Either' , field=False, min=-1.0, max=1.0, value=0.0, step=0.01, dragCommand=update_skew_either,  changeCommand=complete_skew, adjustableColumn=2  )
    SLIDERS.append(SLIDER_SKEW_BOTH)
    SLIDERS.append(SLIDER_SKEW_EITHER)
    cmds.showWindow(window)

# --------------------------------------------------------------------------- #
# Developer section

if __name__ == '__main__':
    # run(1.0)
    ui()


# Thanks Joe!


