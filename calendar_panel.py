from datetime import datetime, timedelta
import calendar
import bpy
import re

from bpy.types import (
    Panel,
    Scene,
    PropertyGroup,
    Operator,
)
from bpy.props import (
    IntProperty,
    StringProperty,
    PointerProperty,
)
from bpy.utils import (
    register_class,
    unregister_class,
)

bl_info = {
    "name": "Calendar Widget",
    "blender": (3, 6, 5),
    "category": "Tools",
    "location": "View 3D > UI (N Panel)",
    "version": (1, 1, 0),
    "author": "Gorgious56,Hesido",
    "description": "Simple Panel that lets the user input a date/time and set keyframes on a custom property of choice",
    "doc_url": "https://github.com/Gorgious56"
}

class AddDateKeyFrame(Operator):
    """Add Date As KeyFrame"""
    bl_idname = "scene.add_datekeyframe"
    bl_label = "Add Date Keyframe"
    
    def evaluate_path(self, path, alternative_root):
        # Regular expression pattern to match segments of the path
        if(path is None or path == ""):
            return (None, None, None)
        pattern = r'(.+?)\.|(?:\["(.+?)"\])|([^"\[\]]+)'
        segments = re.findall(pattern, path)
        parent_obj = None
        enumerate_from = 0

        # If full path, start with bpy
        if segments[0][0] == "bpy":
            current_obj = bpy
            enumerate_from = 1
        else:
            current_obj = alternative_root

        for segment in segments[enumerate_from:]:
            prop_name = segment[0] or segment[1] or segment[2]
            
            # Check if the property exists
            if hasattr(current_obj, prop_name):
                parent_obj = current_obj
                current_obj = getattr(current_obj, prop_name)
            else:
                if isinstance(current_obj, list):
                    # Check if the property is an indexed attribute in a list
                    index = int(prop_name)  # Extract the index
                    if 0 <= index < len(current_obj):
                        parent_obj = current_obj
                        current_obj = current_obj[index]
                    else:
                        return (None, None, None)  # Index out of range
                elif prop_name in current_obj:
                    parent_obj = current_obj
                    current_obj = current_obj[prop_name]
                else:
                    return (None, None, None)  # Key not found
        return (current_obj, parent_obj, prop_name)

    def SetKeyFrameWithPath(self, path, value, context):
        obj, parent_obj, prop_name = self.evaluate_path(path, context.scene)
        if (obj != None):
            print(parent_obj)
            print(prop_name)
            if hasattr(parent_obj, prop_name):
                print(datetime.timestamp(date))
                setattr(parent_obj, prop_name, value)
            else:
                if isinstance(parent_obj, list):
                    index = int(prop_name) 
                    if 0 <= index < len(parent_obj):
                        parent_obj[index] = value
                elif prop_name in parent_obj:
                    parent_obj[prop_name] = value
            if(hasattr(parent_obj,"keyframe_insert") and callable(getattr(parent_obj, "keyframe_insert"))):
                parent_obj.keyframe_insert(data_path= f'["{prop_name}"]', frame=context.scene.frame_current)

    def execute(self, context):
        props = context.scene.calendar_props
        timestamp = datetime.timestamp(datetime(props.year, props.month, props.day, props.hour, props.minute, props.second))
        
        self.SetKeyFrameWithPath(props.timestamp_datapath, timestamp, context)
       
        return {'FINISHED'}

class CalendarProps(PropertyGroup):

    def time_updated(self, context):
        props = context.scene.calendar_props
        #print("Trying to update dependencies")
        for ob in bpy.data.objects:
            update_dependencies(ob)
    
    year: IntProperty(min=1, soft_min=1900, soft_max=2100,
                      max=9999, default=datetime.now().year,
        update = time_updated)
    month: IntProperty(min=1, max=12, default=datetime.now().month,
        update = time_updated)
    day: IntProperty(min=1, max=31,
        update = time_updated)
    hour: IntProperty(min=0, max=23, default=datetime.now().hour,
        update = time_updated)
    minute: IntProperty(min=0, max=59, default=datetime.now().minute,
        update = time_updated)
    second: IntProperty(min=0, max=59, default=datetime.now().second,
        update = time_updated)
    timestamp_datapath: StringProperty()
    

class Calendar_OT_Change_Date(Operator):
    """Change date in the scene properties"""
    bl_idname = "calendar.change_date"
    bl_label = "Change Date"
    bl_options = {'UNDO', 'INTERNAL'}

    year: IntProperty()
    month: IntProperty()
    day: IntProperty()
    hour: IntProperty()
    minute: IntProperty()
    second: IntProperty()

    def execute(self, context):
        props = context.scene.calendar_props
        if self.month > 12:
            self.year += 1
            self.month = 1
        elif self.month <= 0:
            self.year -= 1
            self.month = 12
        
        print(self.day)
        if self.day:
            props.day = self.day
        if self.month:
            props.month = self.month
        if self.year:
            props.year = self.year
        if self.hour:
            props.hour = self.hour
        if self.minute:
            props.minute = self.minute
        if self.second:
            props.second = self.second
            
        return {'FINISHED'}


class CalendarPanel(Panel):
    """Task Tracker Panel in the 3d View"""
    bl_idname = "CALENDAR_PANEL_PT_layout"
    bl_label = "Calendar Widget"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Calendar'
    

    def draw(self, context):
        props = context.scene.calendar_props
        day = props.day
        month = props.month
        year = props.year
        now = datetime.now()

        layout = self.layout

        split = layout.split(factor=0.1)
        self.change_day_op(
            split,
            "",
            {
                "month": now.month,
                "year": now.year,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
            },
            icon='RECOVER_LAST'
        )
        header = split.split(factor=0.7)

        row = header.row()
        row.label(text=calendar.month_name[month].upper())
        row.prop(props, "year", text="", emboss=False)

        row = header.row(align=True)
        for txt, inc in zip(("<", ">"), (-1, 1)):
            self.change_day_op(
                row, txt, {"month": month + inc, "year": year})

        date = datetime(year, month, 1)

        weekday = date.weekday()

        for r in range(7):
            new_date = None
            row = layout.row(align=True)
            for c in range(8):
                col = row.column(align=True)
                label = ""
                if c == 0:
                    if r == 0:
                        label = "#"
                    else:
                        label = "w" + \
                            str((date + timedelta(days=(r - 1) * 7)
                                 ).isocalendar()[1])
                elif r == 0:
                    label = calendar.day_name[c - 1][0:3].upper()
                else:
                    new_date = date + \
                        timedelta(days=c - 1 + (r - 1) * 7 - weekday)
                    label = new_date.day
                if isinstance(label, int) and new_date:
                    self.change_day_op(
                        col,
                        str(label),
                        {
                            "day": label,
                            "month": new_date.month,
                            "year": new_date.year,
                        },
                        emboss=new_date.month == month,
                        depress=(new_date.day == day
                                 and new_date.month == month
                                 and new_date.year == year))
                else:
                    col.label(text=str(label))
        layout.separator()
        row = layout.row()
        for p, t in zip(("hour", "minute", "second"), (":", "''", "'")):
            split = row.split(factor=0.8)
            split.prop(props, p, text="")
            split.label(text=t)
                
        row = layout.row()
        split = row.split(factor=0.4)
        split.prop(props, "timestamp_datapath", text="Path")
        
        # Second Column: Button
        operator = split.operator(AddDateKeyFrame.bl_idname, text="Add Date Keyframe", icon="KEYFRAME")


    @staticmethod
    def change_day_op(layout, txt, op_settings, emboss=True, depress=False, icon=None):
        if icon:
            op = layout.operator(Calendar_OT_Change_Date.bl_idname,
                                 text=txt, emboss=emboss, depress=depress, icon=icon)
        else:
            op = layout.operator(Calendar_OT_Change_Date.bl_idname,
                                 text=txt, emboss=emboss, depress=depress)
        for op_prop, op_value in op_settings.items():
            setattr(op, op_prop, op_value)

classes = (
    AddDateKeyFrame,
    CalendarPanel,
    CalendarProps,
    Calendar_OT_Change_Date,
)


def register():
    for cls in classes:
        register_class(cls)
    Scene.calendar_props = PointerProperty(type=CalendarProps)

def unregister():
    del Scene.calendar_props
    for cls in reversed(classes):
        unregister_class(cls)

if __name__ == "__main__":
    # This will create a subpanel in the "N" panel in the 3D Viewport
    # To get the selected Date / time :
    # props = bpy.context.scene.calendar_props
    # print(props.year, props.month, props.day, props.hour, props.minute, props.second)
    register()


def update_dependencies(ob):
    def updateExp(d):
        # https://blender.stackexchange.com/questions/118350/how-to-update-the-dependencies-of-a-driver-via-python-script
        d.driver.expression += " "
        d.driver.expression = d.driver.expression[:-1]
    try:
        drivers = ob.animation_data.drivers
        for d in drivers:
            print(d)
            updateExp(d)
            print("Updated")
    except AttributeError:
        return
