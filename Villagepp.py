from sys import exit

import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb

from PIL import ImageFont, ImageDraw, ImageTk, Image

from aiv import Aiv, AIV_SIZE, Building, BuildingId, TroopId

# TODO: settings.json
lang = "en"

# TODO: language data
lang_data = {
    "File": {
        "en": "File",
        "de": "Datei"},

    "New": {
        "en": "New",
        "de": "Neu"
    }
}


class Villagepp(tk.Tk):
    def __init__(self, master = None):
        tk.Tk.__init__(self)

        self.aiv_path = None
        self.aiv = Aiv()

        self.geometry("640x480")
        self.wm_title("Village++")
        self.iconphoto(False, tk.PhotoImage(file="res/logo.png"))

        self.frame_map       = tk.Frame(self)
        self.frame_navbar    = tk.Frame(self)
        self.frame_category  = tk.Frame(self)
        self.frame_menu      = tk.Frame(self)

        # populate widgets in frame
        self.map        = self.Map      (self.frame_map,     self)
        self.navbar     = self.Navbar   (self.frame_navbar,  self)
        self.category   = self.Category (self.frame_category,self)
        self.menu       = self.Menu     (self.frame_menu,    self, "Ca") 
        
        self.menubar    = self.Menubar(self)
    
        # define grid
        self.frame_map      .grid(row = 0, column = 0, sticky="nsew", rowspan = 3)
        self.frame_navbar   .grid(row = 0, column = 1, sticky="nsew")
        self.frame_category .grid(row = 1, column = 1, sticky="nsew")
        self.frame_menu     .grid(row = 2, column = 1, sticky="nsew")

        self.grid_columnconfigure(0, weight = 3)
        self.grid_columnconfigure(1, weight = 2)
        self.grid_rowconfigure(0, weight = 1)
        self.grid_rowconfigure(1, weight = 1)
        self.grid_rowconfigure(2, weight = 3)

        # all bindings
        self.bind()

    def bind(self):
        # global menubar
        self.bind_all("<Control-n>",        self.new)
        self.bind_all("<Control-o>",        self.open)
        self.bind_all("<Control-s>",        self.save)
        self.bind_all("<Control-Shift-s>",  self.save_as)
        # self.bind_all("<Control-Shift-e>",  self.export)
        self.bind_all("<Control-plus>",     self.map.zoom_in)
        self.bind_all("<Control-minus>",    self.map.zoom_out)

        # global map
        self.bind_all("<q>",            self.step_prev)
        self.bind_all("<Control-q>",    self.step_first)
        self.bind_all("<e>",            self.step_next)
        self.bind_all("<Control-e>",    self.step_last)

        self.bind_all("<w>",            self.map._move_north)
        self.bind_all("<a>",            self.map._move_west)
        self.bind_all("<s>",            self.map._move_south)
        self.bind_all("<d>",            self.map._move_east)
        
        # on map
        self.map.canvas.bind("<Button-1>",      self.map.on_click)
        self.map.canvas.bind("<B1-Motion>",     self.map.move_mouse)
        self.map.canvas.bind("<Button-3>",      self.map.deselect)
        self.map.canvas.bind("<Configure>",     self.map.on_resize)
        self.map.canvas.bind("<Motion>",        self.map.on_drag)

        # other
        self.protocol("WM_DELETE_WINDOW",   self.close)

    class Menubar(tk.Frame):
        def __init__(self, parent):
            menubar = tk.Menu(parent)
            parent.config(menu = menubar)

            # file menu
            file_menu = tk.Menu(menubar, tearoff = 0)
            menubar.add_cascade(label=lang_data["File"][lang], menu = file_menu)

            file_menu.add_command(label=lang_data["New"][lang],     command = parent.new,     accelerator = "Ctrl+N")
            file_menu.add_command(label = "Open...",                command = parent.open,    accelerator = "Ctrl+O")
            file_menu.add_command(label = "Save",                   command = parent.save,    accelerator = "Ctrl+S")
            file_menu.add_command(label = "Save as...",             command = parent.save_as, accelerator = "Ctrl+Shift+S")
            file_menu.add_separator()
            # TODO: export popup
            file_menu.add_command(label = "Export Preview...",      command = parent.export_preview)
            file_menu.add_command(label = "Export Full...",         command = parent.export_full)

            file_menu.add_separator()
            file_menu.add_command(label= "Exit",                    command = parent.close)
            
            # view menu
            view_menu = tk.Menu(menubar, tearoff = 0)
            menubar.add_cascade(label= "View", menu = view_menu)

            view_menu.add_command(label = "Zoom in",                command = parent.map.zoom_in,   accelerator = "Ctrl++")
            view_menu.add_command(label = "Zoom out",               command = parent.map.zoom_out,  accelerator = "Ctrl+-")

            # help menu
            help_menu = tk.Menu(menubar, tearoff = 0)   
            menubar.add_cascade(label= "Help", menu = help_menu)

            help_menu.add_command(label = "About...",               command = parent.about)

    class Map(tk.Frame):
        def __init__(self, frame_parent, parent):
            tk.Frame.__init__(self, frame_parent)

            self.canvas = tk.Canvas(frame_parent)

            self.parent = parent
            self.frame_parent = frame_parent

            self.canvas.grid(row = 0, column = 0, sticky = "nsew")
            frame_parent.columnconfigure(0, weight = 1)
            frame_parent.rowconfigure(0, weight = 1)

            self.tile_size = 32
            self.shadow = None
            #dictionaries, building/troop-id as key, corresponding tiles (of type Image) as value
            self.building_tiles = {}
            self.troop_tiles = {}
            self.load_tileset("res/tiles.bmp")

            self.origin = (0,0) #in pixel
            self.last_mouse_pos = (0,0)
            self.selected = None

            self.surface = Image.new("RGBA", (self.tile_size*AIV_SIZE, self.tile_size*AIV_SIZE), (0, 0, 0, 255))
            self.redraw_surface()

            #size of whole editor
            frame_width = self.canvas.winfo_width()
            frame_height = self.canvas.winfo_height()
            self.screenTSize = ((frame_width + self.tile_size - 1)//self.tile_size, (frame_height + self.tile_size - 1)//self.tile_size)
            self.screen_size = (frame_width, frame_height)

            blackground = Image.new("RGB", self.screen_size, (0, 0, 0))
            blackground.paste(self.surface, self.origin)

            self.screen = ImageTk.PhotoImage(blackground)
            self.canvas.create_image(0, 0, image=self.screen, anchor=tk.NW)

        def zoom_out(self, e = None):
            (x0, y0) = self.origin #in units of pixel

            if(self.tile_size != 1):
                self.tile_size = self.tile_size//2
                self.resize_tileset()

                (frame_width, frame_height) = self.screen_size
                #zoom_in out to center of the screen
                self.origin = (x0//2 + frame_width//4, y0//2 + frame_height//4)

                self.screenTSize = ((frame_width + self.tile_size - 1)//self.tile_size, (frame_height + self.tile_size - 1)//self.tile_size)

                self.surface = Image.new("RGBA", (self.tile_size*AIV_SIZE, self.tile_size*AIV_SIZE), (0, 0, 0, 255))
                self.redraw_partially((0,0), self.screenTSize)
                self.update_screen()

        def zoom_in(self, e = None):
            (x0, y0) = self.origin #in units of pixel
            (frame_width, frame_height) = self.screen_size

            self.tile_size = self.tile_size*2
            self.resize_tileset()

            #zoom_in on center of the screen
            self.origin = (x0*2 - frame_width//2, y0*2 - frame_height//2)

            self.screenTSize = ((frame_width + self.tile_size - 1)//self.tile_size, (frame_height + self.tile_size - 1)//self.tile_size)


            self.surface = Image.new("RGBA", (self.tile_size*AIV_SIZE, self.tile_size*AIV_SIZE), (0, 0, 0, 255))
            self.redraw_partially((0,0), self.screenTSize)
            self.update_screen()

        def deselect(self, e):
            self.selected = None

        def coordinate(self, position):
            (x, y) = position
            (x0, y0) = self.origin
            x = (x - x0)//self.tile_size
            y = (y - y0)//self.tile_size
            return (x, y)

        def on_click(self, e):
            x = e.x
            y = e.y
            self.last_mouse_pos = (x, y)
            if(self.selected != None):
                kind = self.selected[0]
                position = self.coordinate((x, y))

                if(kind == "Building"):
                    buildingId = self.selected[1]
                    building = Building(buildingId)

                    if(self.parent.aiv.building_isplaceable(building, position)):
                        self.parent.aiv.building_place(building, position)

                        (y_size, x_size) = building.mask_full().shape
                        #self.on_drag(self, e)
                        #TODO: update shadow, atm the shadow is still green if the mouse isnt moved directly after the building is placed/mouse is clicked
                        self.redraw_partially((x, y), (x_size, y_size))
                elif(kind == "Unit"):
                    unitId = self.selected[1]
                    self.parent.aiv.troop_place(unitId, position)
                    self.redraw_partially((x, y), (1, 1))
                elif(kind == "DeleteUnit"):
                    self.parent.aiv.troop_remove(position)
                    self.redraw_partially((x, y), (1, 1))
                elif(kind == "DeleteBuilding"):
                    (xDelete, yDelete) = position
                    buildingId = self.parent.aiv.bmap_id[yDelete, xDelete]
                    buildingId = BuildingId(buildingId).name
                    building = Building(buildingId)
                    self.parent.aiv.building_remove(position)

                    (xSize, ySize) = building.mask_full().shape
                    #increase size that is redrawn, since the mouse could also click on the lower right of the building
                    self.redraw_partially((x - xSize*self.tile_size, y - ySize*self.tile_size), (2*xSize, 2*ySize))
                elif(kind == "Wall-like"):
                    #TODO: on first click: save current position
                    #      on second click: build wall/whatevs from first position to current position
                    pass

                self.update_screen()

        def on_drag(self, e):
            x = e.x
            y = e.y
            self.last_mouse_pos = (x, y)
            if(self.selected != None):
                shadow = None
                (x_tile, y_tile) = self.coordinate((x, y))
                kind = self.selected[0]

                if(kind == "Building"):
                    buildingId = self.selected[1]
                    building = Building(buildingId)
                    mask = building.mask_full()
                    (y_size, x_size) = mask.shape

                    tile = None
                    if(self.parent.aiv.building_isplaceable(building, (x_tile, y_tile))):
                        tile = Image.new("RGBA", (self.tile_size, self.tile_size), (0, 255, 0, 255))
                    else:
                        tile = Image.new("RGBA", (self.tile_size, self.tile_size), (255, 0, 0, 255))

                    shadow = Image.new("RGBA", (x_size*self.tile_size, y_size*self.tile_size), (0, 0, 0, 0))
                    for x in range(x_size):
                        for y in range(y_size):
                            shadow.paste(tile, (x*self.tile_size, y*self.tile_size))
                elif(kind == "Unit"):
                    unitId = self.selected[1]
                    shadow = Image.new("RGBA", (self.tile_size, self.tile_size), (0, 255, 0, 127))
                elif(kind == "DeleteUnit" or kind == "DeleteBuilding"):
                    shadow = Image.new("RGBA", (self.tile_size, self.tile_size), (255, 0, 0, 127))
                elif(kind == "Wall-like"):
                    pass
                    #is not yet implemented in on_click
                self.shadow = shadow
                self.update_screen()
            else:
                self.shadow = None
                self.update_screen()

        def move_keyboard(self, e = None, direction = None):
            (x, y) = (0,0)

            if (direction == 'N'):
                y += self.tile_size
            elif (direction == 'NW'):
                pass
            elif (direction == 'W'):
                x += self.tile_size
            elif (direction == 'SW'):
                pass
            elif (direction == 'S'):
                y -= self.tile_size
            elif (direction == 'SE'):
                pass
            elif (direction == 'E'):
                x -= self.tile_size
            elif (direction == 'NE'):
                pass
            self.move_map((x,y))

        def _move_north(self, e = None):
            self.move_keyboard(e, 'N')
        def _move_north_west(self, e = None):
            self.move_keyboard(e, 'NW')
        def _move_west(self, e = None):
            self.move_keyboard(e, 'W')
        def _move_south_west(self, e = None):
            self.move_keyboard(e, 'SW')
        def _move_south(self, e = None):
            self.move_keyboard(e, 'S')
        def _move_south_east(self, e = None):
            self.move_keyboard(e, 'SE')
        def _move_east(self, e = None):
            self.move_keyboard(e, 'E')
        def _move_north_east(self, e = None):
            self.move_keyboard(e, 'NE')


        def move_mouse(self, e):
            (x0, y0) = self.last_mouse_pos
            xDiff = e.x - x0
            yDiff = e.y - y0
            self.last_mouse_pos = (e.x, e.y)

            self.move_map((xDiff, yDiff))

        def move_map(self, posDiff):
            (x, y) = self.origin
            (moveX, moveY) = posDiff
            x += moveX
            y += moveY
            self.origin = (x, y)

            self.redraw_partially((0,0), self.screenTSize)

            self.update_screen()

        def update_screen(self):
            frame_width = self.canvas.winfo_width()
            frame_height = self.canvas.winfo_height()
            self.screenTSize = ((frame_width + self.tile_size - 1)//self.tile_size, (frame_height + self.tile_size - 1)//self.tile_size)
            self.screen_size = (frame_width, frame_height)

            self.screen = Image.new("RGBA", self.screen_size, (0, 0, 127, 255))
            self.screen.paste(self.surface, self.origin)

            if(self.shadow != None):
                (x_tile, y_tile) = self.coordinate(self.last_mouse_pos)
                (x0, y0) = self.origin

                xPos = x_tile*self.tile_size + x0
                yPos = y_tile*self.tile_size + y0

                self.screen.paste(self.shadow, (xPos, yPos))
            self.screen = ImageTk.PhotoImage(self.screen)

            self.canvas.create_image(0, 0, image=self.screen, anchor=tk.NW)

        def on_resize(self, e):
            frame_width = self.canvas.winfo_width()
            frame_height = self.canvas.winfo_height()
            self.screenTSize = ((frame_width + self.tile_size - 1)//self.tile_size, (frame_height + self.tile_size - 1)//self.tile_size)
            self.screen_size = (frame_width, frame_height)

            self.redraw_partially(self.origin, self.screenTSize)
            self.update_screen()

        def draw_unit(self, position):
            (x0, y0) = position
            (x_size, y_size) = (1,1)
            for x in range(x0, x0+x_size):
                for y in range(y0, y0+y_size):
                    troopId = self.parent.aiv.tmap[y, x]
                    if(troopId != 0):
                        troopTile = self.troop_tiles[troopId]
                        background = self.surface.crop((x*self.tile_size, y*self.tile_size, (x+1)*self.tile_size, (y+1)*self.tile_size))
                        newMapTile = Image.alpha_composite(background, troopTile)
                        # newMapTile.show()
                        self.surface.paste(newMapTile, (x*self.tile_size, y*self.tile_size))

        #        def drawBuildingOnMap(self, building, position):
        #            (x0, y0) = position
        #            mask = building.mask_full()
        #            (x_size, y_size) = mask.shape
        #
        #            namePositions = []
        #            for x in range(x0, x0+x_size):
        #                for y in range(y0, y0+y_size):
        #                    buildingId = self.parent.aiv.bmap_id[y, x]
        #                    buildingSurface = None
        #                    #grass
        #                    if(buildingId == BuildingId.NOTHING):
        #                        buildingSurface = self.building_tiles[buildingId][self.parent.aiv.gmap[y, x]]
        #                    #moat or pitch or any other tile that doesn't have an orientation - walls?
        #                    elif(buildingId < 30):
        #                        buildingSurface = self.building_tiles[buildingId]
        #                    else:
        #                        buildingSurface = self.building_tiles[buildingId][self.parent.aiv.bmap_tile[y, x]]
        #                    if(self.parent.aiv.bmap_step[y, x] >= self.parent.aiv.step_cur):
        #                        buildingSurface.putalpha(127)
        #                    self.surface.paste(buildingSurface, (x*self.tile_size, y*self.tile_size))
        #                    if(self.parent.aiv.bmap_tile[y, x] == 1):
        #                        namePositions.append((x,y))
        #
        #                    troopId = self.parent.aiv.tmap[y, x]
        #                    if(troopId != 0):
        #                        troopTile = self.troop_tiles[troopId]
        #
        #                        background = self.surface.crop((x*self.tile_size, y*self.tile_size, (x+1)*self.tile_size, (y+1)*self.tile_size))
        #                        newMapTile = Image.alpha_composite(background, troopTile)
        #                        self.surface.paste(newMapTile, (x*self.tile_size, y*self.tile_size))


        def redraw_partially(self, origin, size):
            (x0, y0) = self.coordinate(origin)
            (x_size, y_size) = size

            x0 = max(0, x0)
            y0 = max(0, y0)

            x_max = min(x0+x_size, AIV_SIZE)
            y_max = min(y0+y_size, AIV_SIZE)

            namePositions = []
            for x in range(x0, x_max):
                for y in range(y0, y_max):
                    buildingId = self.parent.aiv.bmap_id[y, x]
                    buildingSurface = None
                    #grass
                    if(buildingId == BuildingId.NOTHING):
                        buildingSurface = self.building_tiles[buildingId][self.parent.aiv.gmap[y, x]]
                    #moat or pitch or any other tile that doesn't have an orientation - walls?
                    elif(buildingId < 30):
                        buildingSurface = self.building_tiles[buildingId]
                    else:
                        buildingSurface = self.building_tiles[buildingId][self.parent.aiv.bmap_tile[y, x]]
                    if(self.parent.aiv.bmap_step[y, x] >= self.parent.aiv.step_cur):
                        buildingSurface.putalpha(127)
                    self.surface.paste(buildingSurface, (x*self.tile_size, y*self.tile_size))
                    if(self.parent.aiv.bmap_tile[y, x] == 1):
                        namePositions.append((x,y))

                    troopId = self.parent.aiv.tmap[y, x]
                    if(troopId != 0):
                        troopTile = self.troop_tiles[troopId]

                        background = self.surface.crop((x*self.tile_size, y*self.tile_size, (x+1)*self.tile_size, (y+1)*self.tile_size))
                        newMapTile = Image.alpha_composite(background, troopTile)
                        self.surface.paste(newMapTile, (x*self.tile_size, y*self.tile_size))


        def redraw_surface(self): #redraws the map-surface, but not the screen
            self.surface = Image.new("RGBA", (self.tile_size*AIV_SIZE, self.tile_size*AIV_SIZE), (0, 0, 0, 255))
            namePositions = []
            for x in range(0, AIV_SIZE): 
                for y in range(0, AIV_SIZE):
                    buildingId = self.parent.aiv.bmap_id[y, x]
                    buildingSurface = None
                    #grass
                    if(buildingId == BuildingId.NOTHING):
                        buildingSurface = self.building_tiles[buildingId][self.parent.aiv.gmap[y, x]]
                    #moat or pitch or any other tile that doesn't have an orientation - walls?
                    elif(buildingId < 30):
                        buildingSurface = self.building_tiles[buildingId]
                    else:
                        buildingSurface = self.building_tiles[buildingId][self.parent.aiv.bmap_tile[y, x]]
                    if(self.parent.aiv.bmap_step[y, x] >= self.parent.aiv.step_cur):
                        buildingSurface.putalpha(127)
                    self.surface.paste(buildingSurface, (x*self.tile_size, y*self.tile_size))
                    if(self.parent.aiv.bmap_tile[y, x] == 1):
                        namePositions.append((x,y))

                    #draw troops "above" buildings
                    troopId = self.parent.aiv.tmap[y, x]
                    if(troopId != 0):
                        troopTile = self.troop_tiles[troopId]

                        background = self.surface.crop((x*self.tile_size, y*self.tile_size, (x+1)*self.tile_size, (y+1)*self.tile_size))
                        newMapTile = Image.alpha_composite(background, troopTile)
                        self.surface.paste(newMapTile, (x*self.tile_size, y*self.tile_size))
            #        for pos in namePositions:
            #            (x, y) = pos
            #            size = self.parent.aiv.bmap_size[y, x]
            #
            #            #for nice transparent text: crop underlying map, alpha_composite with text-image, then paste back to map
            #
            # #           #crop building
            # #           im = inputBMP.crop((left, upper, right, lower))
            # #           #TODO: buildings of size 2 might not get properly cropped, but atm they don't even have text since they have no tile with bmap_tile == 1
            # #           left = x - (size-1)/2
            # #           upper = y - (size-1)/2
            # #           building = self.surface.crop((left, upper, right, lower))
            #
            #            #blank image for text, transparent
            #            txt = Image.new("RGBA", (self.tile_size*size, self.tile_size*size), (0, 0, 255, 0))
            #            #get a font
            #            font = ImageFont.load_default()
            #            #get a drawing context from blank image
            #            d = ImageDraw.Draw(txt)
            #            #draw text to image
            #            d.text(((self.tile_size*size)//2, (self.tile_size*size)//2), str(BuildingId(self.parent.aiv.bmap_id[y, x]).name), fill="black", anchor="mm", font=font)
            #            self.surface.paste(txt, (x*self.tile_size, y*self.tile_size))

        def get_input_tile(self, x, y, inputBMP):
            originOffset = 1 #first tile offset in x/y-direction
            bmptile_size = 32 #edge length of a tile
            tileGap = 1 #space between tiles

            left = originOffset + x*(bmptile_size + tileGap)
            upper = originOffset + y*(bmptile_size + tileGap)
            right = left + bmptile_size
            lower = upper + bmptile_size

            im = inputBMP.crop((left, upper, right, lower))
            return im

        def resize_tileset(self):
            for key in self.building_tiles:
                if(isinstance(self.building_tiles[key], type(Image))):
                    self.building_tiles[key] = self.building_tiles[key].resize((self.tile_size, self.tile_size))
                elif(isinstance(self.building_tiles[key], list)):
                    newImageList = []
                    for i in range(len(self.building_tiles[key])):
                        newImageList.append(self.building_tiles[key][i].resize((self.tile_size, self.tile_size)))
                    self.building_tiles[key] = newImageList
            for key in self.troop_tiles:
                self.troop_tiles[key] = self.troop_tiles[key].resize((self.tile_size, self.tile_size))
                        

        def load_tileset(self, path):
            rawBMP = Image.open(path)
            rawBMP.putalpha(255)
            for elem in BuildingId:
                imageList = []
                # grass
                if(elem.value == BuildingId.NOTHING):
                    for variation in range(0, 8):
                        imageList.append(self.get_input_tile(8, variation, rawBMP))
                # border
                elif(elem.value == BuildingId.BORDER_TILE):
                    imageList = self.get_input_tile(9, 9, rawBMP)
                # auto
                elif(elem.value == BuildingId.AUTO):
                    imageList = self.get_input_tile(9, 8, rawBMP)
                # walls    
                elif(elem.value == BuildingId.HIGH_WALL):
                    imageList = self.get_input_tile(0, 9, rawBMP)
                elif(elem.value == BuildingId.LOW_WALL):
                    imageList = self.get_input_tile(1, 9, rawBMP)
                elif(elem.value == BuildingId.HIGH_CRENEL):
                    imageList = self.get_input_tile(0, 0, rawBMP)
                elif(elem.value == BuildingId.LOW_CRENEL):
                    imageList = self.get_input_tile(1, 0, rawBMP)
                #stairs
                elif(elem.value == BuildingId.STAIRS_1):
                    imageList = self.get_input_tile(9, 0, rawBMP)
                elif(elem.value == BuildingId.STAIRS_2):
                    imageList = self.get_input_tile(9, 1, rawBMP)
                elif(elem.value == BuildingId.STAIRS_3):
                    imageList = self.get_input_tile(9, 2, rawBMP)
                elif(elem.value == BuildingId.STAIRS_4):
                    imageList = self.get_input_tile(9, 3, rawBMP)
                elif(elem.value == BuildingId.STAIRS_5):
                    imageList = self.get_input_tile(9, 4, rawBMP)
                elif(elem.value == BuildingId.STAIRS_6):
                    imageList = self.get_input_tile(9, 5, rawBMP)
                # moat
                elif(elem.value == BuildingId.MOAT):
                    imageList = self.get_input_tile(8, 8, rawBMP)
                # pitch
                elif(elem.value == BuildingId.PITCH):
                    imageList = self.get_input_tile(8, 9, rawBMP)
                # else
                else:
                    for variation in range(0, 10): #10 different tile-orientations for each color
                        #imageList.append(self.get_input_tile((elem.value-30)//10, variation, rawBMP))
                        imageList.append(self.get_input_tile(elem.value//10 - 3, variation, rawBMP))
                self.building_tiles.update({elem.value : imageList})
            
            for elem in TroopId:
                #blank image for text, transparent
                txt = Image.new("RGBA", (self.tile_size, self.tile_size), (255, 0, 0, 255))
                #get a font
                font = ImageFont.load_default()
                #get a drawing context from blank image
                d = ImageDraw.Draw(txt)
                #draw text to image
                d.text((self.tile_size//2, self.tile_size//2), str(elem.name), fill="black", anchor="mm", font=font)
                self.troop_tiles.update({elem.value : txt})
        
        def save_image(self, path):
            self.surface.save(path)

    class Navbar(tk.Frame):
        def __init__(self, frame_parent, parent):
            tk.Frame.__init__(self, frame_parent)

            self.button_firs    = tk.Button(frame_parent, text = "|<",  command = parent.step_first)
            self.button_prev    = tk.Button(frame_parent, text = "<",   command = parent.step_prev)
            self.slider_step    = tk.Scale(frame_parent, command = parent.update_slider, from_ = 1, to = parent.aiv.step_tot, orient = tk.HORIZONTAL)
            self.slider_step.set(parent.aiv.step_cur)
            self.button_next    = tk.Button(frame_parent, text = ">",   command = parent.step_next)
            self.button_last    = tk.Button(frame_parent, text = ">|",  command = parent.step_last)

            self.button_firs.grid(row = 0, column = 0, sticky="nsew")
            self.button_prev.grid(row = 0, column = 1, sticky="nsew")
            self.slider_step.grid(row = 0, column = 2, sticky="nsew")
            self.button_next.grid(row = 0, column = 3, sticky="nsew")
            self.button_last.grid(row = 0, column = 4, sticky="nsew")
            
            frame_parent.grid_columnconfigure(0, weight=1)
            frame_parent.grid_columnconfigure(1, weight=1)
            frame_parent.grid_columnconfigure(2, weight=2)
            frame_parent.grid_columnconfigure(3, weight=1)
            frame_parent.grid_columnconfigure(4, weight=1)

            frame_parent.grid_rowconfigure(0, weight=1)

    class Category(tk.Frame):
        def __init__(self, frame_parent, parent):
            tk.Frame.__init__(self, frame_parent)
            
            names = ["De", "Wa", "Ca", "Ga", "We", "In", "Mi", "Mo", "Fo", "To", "Go", "Ba"]

            for r in range(0,2):
                frame_parent.grid_rowconfigure(r, weight=1)
                for c in range (0,6):
                    frame_parent.grid_columnconfigure(c, weight=1)
                    idx = 6*r+c
                    tk.Button(frame_parent, text = names[idx], command = lambda idx=idx: self.redraw_menu(parent, names[idx])).grid(row = r, column = c, sticky="nsew")

        def redraw_menu(self, parent, category):
            parent.menu = parent.Menu(parent.frame_menu, parent, category)

    class Menu(tk.Frame):
        def __init__(self, frame_parent, parent, category = "De"):
            tk.Frame.__init__(self, frame_parent)
            self.parent = parent

            if category == "De":
                tk.Button(frame_parent, text = "POINT", command = lambda: self.set_delete_building()).grid(row = 0, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "FLOOD", command = None).grid(row = 1, column = 0, sticky="nsew", columnspan = 2)
                for r in range(2,11):
                    tk.Button(frame_parent, text = "", command = None).grid(row = r, column = 0, sticky="nsew", columnspan = 2)

            elif category == "Wa":
                tk.Button(frame_parent, text = "HIGH_WALL",     command = None).grid(row = 0, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "LOW_WALL",      command = None).grid(row = 1, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "HIGH_CRENEL",   command = None).grid(row = 2, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "LOW_CRENEL",    command = None).grid(row = 3, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "STAIRS",        command = None).grid(row = 4, column = 0, sticky="nsew", columnspan = 2)
                for r in range(5,11):
                    tk.Button(frame_parent, text = "", command = None).grid(row = r, column = 0, sticky="nsew", columnspan = 2)
            
            elif category == "Mi":
                for r in range(0,11):
                    for c in range(0,2):
                        idx = 2*r+c
                        if idx == 0:
                            tk.Button(frame_parent, text = "DELETE",    command = lambda: self.set_delete_unit()).grid(row = 0, column = 0, sticky="nsew")
                        else:
                            enum = TroopId(idx)
                            tk.Button(frame_parent, text = enum.name,   command = lambda l = enum.value: self.set_unit(l)).grid(row = r, column = c, sticky="nsew")

            elif category == "Mo":
                tk.Button(frame_parent, text = "MOAT",  command = None).grid(row = 0, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "PITCH", command = None).grid(row = 1, column = 0, sticky="nsew", columnspan = 2)
                for r in range(2,11):
                    tk.Button(frame_parent, text = "",  command = None).grid(row = r, column = 0, sticky="nsew", columnspan = 2)

            else:
                base = 0
                if category == "Ca":
                    base = 30
                elif category == "Ga":
                    base = 40
                elif category == "We":
                    base = 50
                elif category == "In":
                    base = 60
                elif category == "Fo":
                    base = 70
                elif category == "To":
                    base = 80
                elif category == "Go":
                    base = 90
                elif category == "Ba":
                    base = 100

                for r in range(0,10):
                    try:
                        enum = BuildingId(base+r)
                        tk.Button(frame_parent, text = enum.name, command = lambda l = enum.name: self.set_building(l)).grid(row = r, column = 0, sticky = "nsew", columnspan = 2)
                    except:
                        tk.Button(frame_parent, text = "", command = None).grid(row = r, column = 0, sticky="nsew", columnspan = 2)
                tk.Button(frame_parent, text = "", command = None).grid(row = 10, column = 0, sticky="nsew", columnspan = 2)

            for r in range(0,11):
                frame_parent.grid_rowconfigure(r, weight=1)
                for c in range(0,2):
                    frame_parent.grid_columnconfigure(c, weight=1)
        
        def set_building(self, id):
            self.parent.map.selected = ("Building", id)

        def set_unit(self, id):
            self.parent.map.selected = ("Unit", id)

        def set_delete_building(self):
            self.parent.map.selected = ("DeleteBuilding", 42)

        def set_delete_unit(self):
            self.parent.map.selected = ("DeleteUnit", 69) #nice

    def new(self, e = None):
        self.ask_save()
        self.aiv = Aiv()

        self.update_slider()

    def open(self, e = None):
        self.ask_save()
        
        aiv_path = fd.askopenfilename()

        if aiv_path == "":
            return
        else:
            self.aiv = Aiv(aiv_path)

        self.update_slider()

    def ask_save(self, e = None):
        save = mb.askyesnocancel("Village++", "Save Changes?")

        if save == True:
            self.save_as()
        elif save == False:
            return
        elif save == None:
            return

    def save(self, e = None):
        aiv_path = self.aiv_path

        if aiv_path == None:
            self.save_as()
        else:
            self.aiv.save(aiv_path)

    def save_as(self, e = None):
        aiv_path = fd.asksaveasfilename()

        if aiv_path == None:
            return
        else:
            self.aiv.save(aiv_path)

    def export_preview(self, e = None):
        save = mb.askyesno("Village++", "Do you want to export a preview?")

        if save == True:
            preview_path = fd.asksaveasfilename()
            if preview_path == None:
                return
            else:
                self.aiv.save_preview(preview_path)
        else:
            return
    
    def export_full(self, e = None):
        save = mb.askyesno("Village++", "Do you want to export an image of the full map?")

        if save == True:
            image_path = fd.asksaveasfilename()
            if image_path == None:
                return
            else:
                self.map.save_image(image_path)
        else:
            return

    def about(self, e = None):
        # TODO: implement about screen
        raise NotImplementedError

    def close(self):
        self.ask_save()
        exit()

    def step_next(self, e = None):
        if (self.aiv.step_cur < self.aiv.step_tot):
            self.aiv.step_cur += 1
        self.update_slider()

    def step_prev(self, e = None):
        if (self.aiv.step_cur > 1):
            self.aiv.step_cur -= 1
        self.update_slider()

    def step_first(self, e = None):
        self.aiv.step_cur = 1
        self.update_slider()

    def step_last(self, e = None):
        self.aiv.step_cur = self.aiv.step_tot
        self.update_slider()

    # TODO: something here is still not okay
    def update_slider(self, e = None):
        if e != None:
            self.aiv.step_cur = int(e)
            # print("step_set: ", self.aiv.step_cur, "/", self.aiv.step_tot)
            self.map.redraw_surface()
            self.map.update_screen()
            return
        self.navbar = self.Navbar(self.frame_navbar, self)


if __name__ == "__main__":
    vpp = Villagepp()
    vpp.mainloop()
