# --------------------------------------------------------------------------- #

from maya import cmds

# --------------------------------------------------------------------------- #

GRAPH_EDITOR = 'graphEditor1GraphEd'

# --------------------------------------------------------------------------- #

def run():
    # get the key selection
    if not cmds.animCurveEditor(GRAPH_EDITOR, exists=True):
        cmds.error("No GraphEditor found.")
        return # Cannot find graph editor?

    if not cmds.animCurveEditor(GRAPH_EDITOR, q=True, areCurvesSelected=True):
        cmds.warning("Must select some keys to fit.")
        return

    selected_curves = cmds.keyframe(q=True, selected=True, name=True) or []
    for curve in selected_curves:
        selected_index = cmds.keyframe(curve, q=True, selected=True, indexValue=True)
        num_keys       = cmds.keyframe(curve, q=True, indexValue=True)

        pre_key_pivot  = min(selected_index)-1
        if pre_key_pivot <= 0: pre_key_pivot = 0 # Just in case the first key is selected
        post_key_pivot = max(selected_index)+1
        if post_key_pivot >= len(num_keys): post_key_pivot = max(num_keys) # Just in case the last key is selected

        key_values = []
        for index in selected_index:
            value = cmds.keyframe(curve, q=True, index=(index,), eval=True, valueChange=True)
            key_values.extend(value)

        # get the values of the pivots
        left_pivot  = cmds.keyframe(curve, q=True, index=(pre_key_pivot,), eval=True, valueChange=True)[0]
        right_pivot = cmds.keyframe(curve, q=True, index=(post_key_pivot,), eval=True, valueChange=True)[0]
        key_values.insert(0, left_pivot)
        key_values.append(right_pivot)

        # get the difference between the left pivot and the leftmost selected key
        pre_delta = key_values[1] - left_pivot

        # Shift the entire set to match first pivot
        new_values = []
        for key in key_values[1:-1]:
            new_values.append(key - pre_delta)

        # Offset both the pivot and the end toward the 'floor'
        # Not sure why this works. Stumbled upon it at 2am. Too tired.
        post_delta_scale = (key_values[-1] - left_pivot) / (new_values[-1] - left_pivot)
        
        # Scale set to fit
        new_values_scaled = []
        for index, key in enumerate(new_values):
            new_value = ((key - left_pivot) * post_delta_scale) + left_pivot
            new_values_scaled.append(new_value)
        
        # Do the magic, do the magic!
        for index, key in enumerate(selected_index):
            cmds.keyframe(curve, index=(key,), valueChange=new_values_scaled[index])

