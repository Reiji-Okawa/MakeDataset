import cv2
import os
import shutil
import math
import numpy as np
import matplotlib.pyplot as plt
import sys
import copy
import csv
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from sclolable_frame import ScrollableFrame


class movie_capture_app:
    def __init__(self):
        self.default_fontfamily = "Yu Gothic UI"
        self.default_fontsize = 10
        self.height = int(480)
        self.width = int(640)
        
        self.programTitle = os.path.splitext(__file__)[0]
        
        self.root = tk.Tk()
        self.root.geometry('{}x{}'.format(int(self.width*1.8), int(self.height*1.8)))
        self.fileOpen()
        self.create_window()
        self.__create_menu()
        # print('complete')

    def create_window(self):
        #メニューバーの作成
        self.menubar = tk.Menu(self.root)
        self.filemenu = tk.Menu(self.menubar)
        self.filemenu.add_command(label = '開く', command = self.fileChange)
        self.menubar.add_cascade(label = "file", menu = self.filemenu)
        self.root.config(menu = self.menubar)
        
        #フレームの作成
        heights, widths  = self.videoShape
        
        
        self.makeMainFrame()
        self.makeLabelFrame()
        self.makeSpeedFrame()

    def fileOpen(self):
        #動画ファイルの読み込み
        if(False):#開発用データ
            self.file = 'macro_30fps.avi'
        else:#ファイル選択のホップアップ
            iDir = os.path.abspath(os.path.dirname(__file__))
            self.file = tk.filedialog.askopenfilename(initialdir = iDir)
            if self.file == "":
                return "break"
        self.dir_path = os.path.splitext(os.path.split(self.file)[1])[0]
        print(self.dir_path)
        os.makedirs(self.dir_path, exist_ok=True)

        #動画の大きさ, 長さの取得
        cap = cv2.VideoCapture(str(self.file))
        self.videoShape = [int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))]
        self.videoLength = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        
        #動画のコンバート
        self.videoImage_path = os.path.join(self.dir_path, 'originvideo')
        if(os.path.exists(self.videoImage_path) == False):
            os.makedirs(self.videoImage_path, exist_ok = True)
            digit = len(str(int(cap.get(cv2.CAP_PROP_FRAME_COUNT))))
            for i in range(self.videoLength):
                ret, frame = cap.read()
                img_path = self.videoImage_path + '/image_' +str(i).zfill(digit)+'.png'
                cv2.imwrite(img_path, frame)
        
        self.data_json_path = os.path.join(self.dir_path, 'id_list.json')
        if(os.path.exists(self.data_json_path) == True):
            json_open = open(self.data_json_path, 'r')
            self.registerd_area = json.load(json_open)

        else:
            self.registerd_area = {}


        self.videoFlag = 0 #1 => flow, 0 => stop
        self.analyseFlag = 0
        self.motionFlag = False
        self.rect = False
        self.targetArea2 = np.zeros((4))
        self.targetArea3 = [30, 30, 30, 30]

    def fileChange(self):
        self.fileOpen
        self.window = self.create_window()

    def makeMainFrame(self):
        # print('makeMainFrame')
        h, w = self.videoShape
        if(h!=self.height or w!=self.width):
            self.dx = min(self.height/h, self.width/w)
        else:
            self.dx = 1

        self.mainFrame = ttk.Frame(self.root, width = int(self.width*1.2), height = int(self.height*1.2))
        self.mainFrame.place(x=0, y=0)

        self.movieCanvas = tk.Canvas(self.mainFrame, width = self.width, height = self.height)
        self.movieCanvas.place(x = self.width*0.1, y = self.height*0.1)

        movie_image = cv2.imread(self.videoImage_path + '/image_' +str(0).zfill(len(str(self.videoLength)))+'.png')
        movie_image = self.drow_registerd_area(movie_image, 0)
        movie_image = cv2.resize(movie_image, (int(w*self.dx), int(h*self.dx)))
        self.movie_image = self.makeTkImage(movie_image, self.root)
        self.movieCanvas.create_image(0, 0, image=self.movie_image, anchor='nw')


        self.scaleFrame = ttk.Frame(self.mainFrame, width = self.width*1.2, height = self.height *0.05)
        self.scaleFrame.place(x = 0, y = self.height*1.15)
        self.scaleButton1 = tk.Button(self.scaleFrame, width = 1, height = 1, text = '>', command = self.videoStart)
        self.scaleButton1.pack(side = tk.LEFT)
        self.scaleButton2 = tk.Button(self.scaleFrame, width = 1, height = 1, text = '||', command = self.videoStop)
        self.scaleButton2.pack(side = tk.LEFT)
        self.sc_val = tk.IntVar()
        self.sc = ttk.Scale(
        self.scaleFrame,
        variable=self.sc_val,
        orient=tk.HORIZONTAL,
        length=self.width,
        from_=0,
        to=self.videoLength-1, 
        command = self.scale)
        self.sc.pack(side = tk.LEFT)

        self.movieCanvas.bind('<ButtonPress-1>', self.onClicked)
        self.movieCanvas.bind('<MouseWheel>', self.onWheel)
        self.movieCanvas.bind('<Motion>', self.onMotion)
        #self.movieCanvas.bind('<ButtonPress-2>', self.cellSave)
        self.movieCanvas.bind('<ButtonPress-2>', self.__do_popup)


    def makeLabelFrame(self):
        # print('makeLabelFrame')
        # h, w = self.videoShape
        self.labelFrame = ttk.Frame(self.root, width = int(self.width*0.6), height = int(self.height*1.2))
        self.labelFrame2 = ScrollableFrame(self.labelFrame, bar_x = False)
        self.labelTop = self.makeLabelTop(self.labelFrame2.scrollable_frame)
        self.labelTop.grid(row = 0, column=0)
        self.id_labels = {}
        if(('ids' in self.registerd_area)==True):
            # print(self.registerd_area['ids'].keys())
            for i, j in enumerate(self.registerd_area['ids'].keys()):
            # for i, j in enumerate([0, 1]):
                self.id_labels[str(j)] = self.make_manage_plate(self.labelFrame2.scrollable_frame, self.height, self.width, j)
                self.id_labels[str(j)]['range_entry_a'].insert(tk.END, self.registerd_area['ids'][str(j)]['start'])
                self.id_labels[str(j)]['range_entry_b'].insert(tk.END, self.registerd_area['ids'][str(j)]['end'])

        else:
            self.registerd_area['ids'] = {}
            self.workId = 1
        self.labelFrame2.canvas.configure(width= int(self.width*0.5), height = int(self.height*0.6))
        self.labelFrame2.pack()
        self.labelFrame.place(x=int(self.width*1.2), y=0)

    def makeLabelTop(self, master):
        # print('makeLabelTop')
        frame = ttk.Frame(master, width = self.width*0.5)
        font_set = ('MSゴシック', '10', 'normal')
        id_label = ttk.Label(frame, text='id', background='white', font=font_set, width = 5, anchor=tk.CENTER)
        label_label = ttk.Label(frame, text='label', background='white', font=font_set, width = 10, anchor=tk.CENTER)
        range_label = ttk.Label(frame, text='range', background='white', font=font_set, width = 15, anchor=tk.CENTER)
        command_label = ttk.Label(frame, text='commnad', background='white', font=font_set, width = 10, anchor=tk.CENTER)

        id_label.grid(row=0, column=1)
        label_label.grid(row=0, column=2)
        range_label.grid(row=0, column=3)
        command_label.grid(row=0, column=4)
        return frame

    def make_manage_plate(self, master, h, w, id):
        manage_plate = {}
        manage_plate['id'] = id
        font_set = ('MSゴシック', '10', 'normal')
        manage_plate['frame'] = ttk.Frame(master, width = w*0.8, height = h*0.1)
        manage_plate['select_check_value'] = tk.BooleanVar()
        manage_plate['select_check'] = ttk.Checkbutton(manage_plate['frame'], command= lambda:self.select_get(manage_plate['id']), variable=manage_plate['select_check_value'])
        manage_plate['id_label'] = ttk.Label(manage_plate['frame'], text=str(id), background='white', font=font_set, width = 5, anchor=tk.E)
        manage_plate['label_text'] = tk.StringVar()
        manage_plate['label_entry'] = ttk.Entry(manage_plate['frame'], font = font_set, width = 10)
        manage_plate['label_send'] = tk.Button(manage_plate['frame'], text = 'ok', command=lambda :self.label_send(manage_plate['id']), font = font_set, width = 2)
        manage_plate['a_text'] = tk.StringVar()
        manage_plate['range_entry_a'] = ttk.Entry(manage_plate['frame'], font = font_set, width = 7)
        manage_plate['range_label'] = ttk.Label(manage_plate['frame'], text='-', background='white', font=font_set, width = 1, anchor=tk.E)
        manage_plate['b_text'] = tk.StringVar()
        manage_plate['range_entry_b'] = ttk.Entry(manage_plate['frame'], font = font_set, width = 7)
        
        # manage_plate['edit_btn'] = tk.Button(manage_plate['frame'], text = '編集', command=lambda :self.edit_plate(manage_plate['id']), font = font_set, width = 4)
        manage_plate['delete_btn'] = tk.Button(manage_plate['frame'], text='削除', command=lambda :self.delete_plate(manage_plate['id']), font = font_set, width = 4)

        manage_plate['select_check'].pack(side=tk.LEFT)
        manage_plate['id_label'].pack(side=tk.LEFT)
        manage_plate['label_entry'].pack(side=tk.LEFT)
        manage_plate['label_send'].pack(side=tk.LEFT)
        manage_plate['range_entry_a'].pack(side=tk.LEFT)
        manage_plate['range_label'].pack(side=tk.LEFT)
        manage_plate['range_entry_b'].pack(side=tk.LEFT)         
        # manage_plate['edit_btn'].pack(side=tk.LEFT)
        manage_plate['delete_btn'].pack(side=tk.LEFT)
        manage_plate['frame'].grid(row=int(id)+1, column = 0)
        return manage_plate

    def select_get(self, id):
        self.captureEnd()
        print('select_get', id)
        self.sc.set(int(self.registerd_area['ids'][str(id)]['end']-1))
        self.scale(int(self.registerd_area['ids'][str(id)]['end']-1), id)
        self.analyseFlag = 1
        self.workId = id
        self.save_dir = os.path.join(self.dir_path, 'Id_'+str(self.workId))
    def label_send(self, id):
        print('label_send', id)
        self.captureEnd()
    def edit_plate(self, id):
        print('edit_plate', id)
        self.captureEnd()

    def delete_plate(self, id):
        print('delete_plate', id)
        for i in range(self.registerd_area['ids'][str(id)]['start'], self.registerd_area['ids'][str(id)]['end']+1):        
            del self.registerd_area[str(i)][str(id)]
        self.id_labels[str(id)]['frame'].grid_forget()
        del self.id_labels[str(id)]
        del self.registerd_area['ids'][str(id)]
        del_dir = os.path.join(self.dir_path, 'Id_'+str(id))
        shutil.rmtree(del_dir)
        self.captureEnd()

    def drow_registerd_area(self, image, time):
        if((str(time) in self.registerd_area) == True):
            for i in self.registerd_area[str(time)].keys():
                x, y, W,H = self.registerd_area[str(time)][i]['place']
                for i in range(H):
                    for j in range(W):
                        image[y+i][x+j] = image[y+i][x+j] * 0.5 + np.array([0, 0, 255])*0.3

        return image

    def drow_selected_area(self, image, time, id):
        if((str(time) in self.registerd_area) == True):
            x, y, W,H = self.registerd_area[str(time)][str(id)]['place']
            for i in range(H):
                for j in range(W):
                    image[y+i][x+j] = image[y+i][x+j] * 0.5 + np.array([0, 255, 0])*0.3

        return image


    def makeSpeedFrame(self):
        h, w = self.videoShape
        self.speedFrame = ttk.Frame(self.root, width = int(self.width*0.6), height = int(self.height*0.2))
        self.speedVal = tk.DoubleVar()
        self.speedSc = ttk.Scale(
            self.speedFrame, 
            variable=self.speedFrame,
            orient=tk.HORIZONTAL,
            length = self.width*0.6, 
            from_=1,
            to=1000,
            command=self.set_speed)
        self.speedSc.pack()
        self.speedFrame.place(x=self.width*1.2, y = self.height*0.6)
        self.speedLabel = ttk.Entry(self.speedFrame)
        self.speedLabel.insert(tk.END, self.speedSc.get())
        self.speedLabel.pack()
        self.speedSc.set(500)
    def set_speed(self, speed):
        self.speed = int(16500/int(float(speed)))
        speed_wrt = int(1000/(self.speed))
        print('set_speed')
        self.speedLabel.delete(0, tk.END)
        self.speedLabel.insert(tk.END, str(speed_wrt))


    def scale(self, movieTime, id=None):
        movieTime = int(float(movieTime))
        h, w = self.videoShape
        self.sc_val2 = movieTime
        digit = len(str(self.videoLength))
        img_path = self.videoImage_path + '/image_' +str(int(movieTime)).zfill(digit)+'.png'
        frame = cv2.imread(img_path)
        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        image_w = copy.deepcopy(frame)
        image_w = np.array(image_w, dtype = 'u1')
        if(id):
            self.Apdate(image_w, movieTime, id)
        else:
            self.Apdate(image_w, movieTime)

    def movie_capture(self, movieTime):
        movieTime = int(float(movieTime))
        h, w = self.videoShape
        digit = len(str(self.videoLength))
        img_path = self.videoImage_path + '/image_' +str(int(movieTime)).zfill(digit)+'.png'
        frame = cv2.imread(img_path)
        image_w = copy.deepcopy(frame)
        image_w = np.array(image_w, dtype = 'u1')

        if(True):
            if((str(movieTime) in self.registerd_area) == False):
                self.registerd_area[str(movieTime)] = {}

        if((str(self.workId) in self.registerd_area[str(movieTime)]) == False):
            self.registerd_area[str(movieTime)][str(self.workId)] = {}       
        x1 = int(self.targetArea2[1])
        y1 = int(self.targetArea2[0])
        x2 = int(self.targetArea2[3])
        y2 = int(self.targetArea2[2])
        # print("x1, x2, y1, y2", x1, x2, y1, y2)
        X1 = int(max(x1, 0))
        X2 = int(min(x2, w-1))
        Y1 = int(max(y1, 0))
        Y2 = int(min(y2, h-1))
        
        imgTarget = copy.deepcopy(frame[Y1:Y2, X1:X2])
        name = 'cell'
        self.registerd_area[str(movieTime)][str(self.workId)]['label'] = name
        self.registerd_area[str(movieTime)][str(self.workId)]['place'] = [X1, Y1, X2-X1, Y2-Y1]
        save_path = os.path.join(self.save_dir, "image_id_{}_{}.png".format(str(self.workId), str(int(movieTime)).zfill(digit)))
        cv2.imwrite(save_path, imgTarget)
        #self.Apdate2(image_w)

        self.Apdate(image_w, movieTime)

    def captureEnd(self):
        self.analyseFlag = 0
        print('Saved')
        
        f2 = open(self.data_json_path, 'w')
        json.dump(self.registerd_area, f2)
        
    def Apdate(self, image_w, movieTime, id=None):
        h, w = self.videoShape
        digit = len(str(self.videoLength))

        if(movieTime+1<self.videoLength):
            img_path = self.videoImage_path + '/image_' +str(int(movieTime+1)).zfill(digit)+'.png'
            frame = cv2.imread(img_path)
            image_w = copy.deepcopy(frame)
            image_w = self.drow_registerd_area(image_w, movieTime+1)
            if(id):
                image_w = self.drow_selected_area(image_w, movieTime+1, id)
        image_w = cv2.resize(image_w, (int(w*self.dx), int(h*self.dx)))
        image_w = np.array(image_w, dtype = "u1")

        self.movie_image = self.makeTkImage(image_w, self.root)

        self.movieCanvas.create_image(0, 0, image=self.movie_image, anchor='nw')
        self.rect = self.movieCanvas.create_rectangle(self.targetArea2[1], self.targetArea2[0], self.targetArea2[3], self.targetArea2[2], tag = 'rect')

        

    def makeTkImage(self, image, master):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_array = Image.fromarray(image_rgb)
        image_tk  = ImageTk.PhotoImage(image_array, master = master)
        return image_tk

    def videoStart(self):
        if(self.videoFlag==0):
            self.videoFlag = 1
            self.scale(self.sc_val.get())
            self.root.after(self.speed, self.videoRenew)

    def videoRenew(self):
        if(self.videoFlag == 1):
            next_time = self.sc_val.get() + 1
            if(next_time<self.videoLength):
                self.sc.set(next_time)
                self.scale(next_time)
                self.root.after(self.speed, self.videoRenew)

            else:
                print('reach last_image')
                self.videoFlag = 0

    def videoStop(self):
        self.videoFlag = 0

    def onClicked(self, event):
        if(self.analyseFlag == 1):
            #print(self.videoStops)
            if(self.videoFlag == 0):
                self.videoFlag = 1
                self.root.after(self.speed, self.onClicked2)
                self.videoFlag = 0
            self.videoFlag = (self.videoFlag+1) % 2
            
        else:
            self.videoFlag = 1
            self.analyseFlag = 1
            h, w = self.videoShape
            time = self.sc_val.get()
            if(True):
                if(('ids' in self.registerd_area)==True):
                    next = 1
                    while((str(next)in self.registerd_area['ids'])==True):
                        next += 1
                    self.workId = next
                else:
                    self.registerd_area['ids'] = {}
                    self.workId = 1

                self.registerd_area['ids'][str(self.workId)]={}
                self.registerd_area['ids'][str(self.workId)]['start'] = time
                self.registerd_area['ids'][str(self.workId)]['end'] = time
                
                self.id_labels[str(self.workId)] = self.make_manage_plate(self.labelFrame2.scrollable_frame, self.height, self.width, self.workId)
                self.id_labels[str(self.workId)]['range_entry_a'].insert(tk.END, str(time))
                self.save_dir = os.path.join(self.dir_path, 'Id_'+str(self.workId))
                # print(self.save_dir)
                os.makedirs(self.save_dir, exist_ok=True)
            
            self.movie_capture(time)
            # self.onClicked2()
            self.root.after(self.speed, self.onClicked2)

    def onClicked2(self):
        if((self.sc_val.get() < self.videoLength-1) and self.videoFlag == 1):
            mv_time = self.sc_val.get() + 1
            self.sc.set(mv_time)
            self.movie_capture(mv_time)

            if(mv_time>=self.registerd_area['ids'][str(self.workId)]['end']):
                self.registerd_area['ids'][str(self.workId)]['end'] = mv_time
                self.id_labels[str(self.workId)]['range_entry_b'].delete(0, tk.END)
                self.id_labels[str(self.workId)]['range_entry_b'].insert(tk.END, str(mv_time))
            self.root.after(30, self.onClicked2)

    def onWheel(self, event):
        print("onWheel")
        print(int(event.delta/120))
        x = int(event.delta/120)
        h, w = self.videoShape
        # d = event.delta
        if(self.rect):
            self.movieCanvas.delete(self.rect)
        if(self.targetArea3[0]>0 and self.targetArea2[0]>0 and self.targetArea3[0]<h-1 and self.targetArea2[0]<h-1):
            self.targetArea3[0] += x * 2
            self.targetArea2[0] += x * -1
        if(self.targetArea3[1]>0 and self.targetArea2[1]>0 and self.targetArea3[1]<w-1 and self.targetArea2[1]<w-1):
            self.targetArea3[1] += x * 2
            self.targetArea2[1] += x * -1
        if(self.targetArea3[2]>0 and self.targetArea2[2]>0 and self.targetArea3[2]<h-1 and self.targetArea2[2]<h-1):
            self.targetArea3[2] += x * 2
            self.targetArea2[2] += x * 1
        if(self.targetArea3[3]>0 and self.targetArea2[3]>0 and self.targetArea3[3]<w-1 and self.targetArea2[3]<w-1):
            self.targetArea3[3] += x * 2
            self.targetArea2[3] += x * 1
        self.movieCanvas.create_image(w, h, image = self.movie_image, anchor = 'nw')
        # print("target3", self.targetArea3)
        # print("target2", self.targetArea2)
        self.rect = self.movieCanvas.create_rectangle(self.targetArea2[1], self.targetArea2[0], self.targetArea2[3], self.targetArea2[2])

    def onMotion(self, event):
        if(self.rect):
            self.movieCanvas.delete(self.rect)

        if(self.motionFlag == False):
            self.targetArea2[0] = event.y - self.targetArea3[0]
            self.targetArea2[1] = event.x - self.targetArea3[1]
            self.targetArea2[2] = event.y + self.targetArea3[2]
            self.targetArea2[3] = event.x + self.targetArea3[3]
            self.rect = self.movieCanvas.create_rectangle(self.targetArea2[1], self.targetArea2[0], self.targetArea2[3], self.targetArea2[2], tag = 'rect')
            self.motionFlag = True
        else:
            y = (event.y - self.targetArea3[0]) - self.targetArea2[0]
            x = (event.x - self.targetArea3[1]) - self.targetArea2[1]
            self.targetArea2[0] = event.y - self.targetArea3[0]
            self.targetArea2[1] = event.x - self.targetArea3[1]
            self.targetArea2[2] = event.y + self.targetArea3[2]
            self.targetArea2[3] = event.x + self.targetArea3[3]
            self.rect = self.movieCanvas.create_rectangle(self.targetArea2[1], self.targetArea2[0], self.targetArea2[3], self.targetArea2[2], tag = 'rect')

    def __do_popup(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def __create_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, background="#111111", foreground="#eeeeee", activebackground="#000000", activeforeground="#ffffff")
        self.menu.add_command(label = "終了", command=self.captureEnd, font=(self.default_fontfamily, self.default_fontsize))
  
    def run(self):
        self.root.mainloop()

movie_capture_app().run()