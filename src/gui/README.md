# GUI Development Guide

## Making Changes to the User Interface

### Files Involved
- `dialog.ui` - Qt Designer UI layout file
- `dialog.h` - Header file with class declarations
- `dialog.cpp` - Implementation file with UI logic

### Common UI Modifications

#### 1. Layout Changes
- Edit `dialog.ui` directly for widget positioning and sizing
- Use Qt Designer or edit XML manually
- Set `minimumSize` and `maximumSize` properties for widgets
- Adjust layout constraints and size policies

#### 2. Adding New UI Elements
1. Add widget to `dialog.ui`
2. Declare slot/member functions in `dialog.h`
3. Implement functionality in `dialog.cpp`
4. Connect signals to slots in constructor

#### 3. Resizing Components
- Modify `minimumSize` property in `dialog.ui`
- Use `setSizePolicy()` in C++ code for dynamic sizing
- Call custom layout functions like `reorganizeLayout()`

### Build Process
```bash
mkdir build && cd build
cmake ..
make
```

### Current Layout Structure
- Left side: Recipe table (enlarged to 500x450px minimum)
- Right side: Controls and output sections
- Status section: Limited height for more recipe table space

### Recent Changes
- Recipe table minimum size increased to 500x450
- Added `reorganizeLayout()` function for better space utilization
- Status and control sections height-constrained to maximize recipe table area