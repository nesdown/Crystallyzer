# _*_ coding: utf-8 _*_
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
import serial
import time

#Data Base for crystalls' parameters
#Name			temperature 	transparency 	resistance 		order 
#
#Galit			0.16-0.20 C     40-50			60-80			4		
#Quartz			0.80-0.90 C		120-150			25-30			3
#Saccharoze 	0.6-0.7	C		250-300			80-90			2			
#Cooperas		0.4-0.5 C  		350-600			120-130			1
#Salt Amonium	0.05-0.1 C 		200-250			50-60			1
#
#SampleName		0.n-0.k	C		10n-10k			n-k				p


root = Tk()
root.wm_title("Crystall Analyzer 1.0")
#root.resizable(width=False, height=False)
root.geometry('{}x{}'.format(850, 630))

#initialize pictures
#diffraction patterns
an1 = PhotoImage(file="an1.png")
an2 = PhotoImage(file="an2.png")
an3 = PhotoImage(file="an3.png")
an4 = PhotoImage(file="an4.png")
an5 = PhotoImage(file="an5.png")
an6 = PhotoImage(file="an6.png")

#geometrical explanations
geom1 = PhotoImage(file="geom1.png")
geom2 = PhotoImage(file="geom2.png")
geom3 = PhotoImage(file="geom3.png")
geom4 = PhotoImage(file="geom4.png")
geom5 = PhotoImage(file="geom5.png")
geom6 = PhotoImage(file="geom6.png")

#coefficients
plast = 0
heat = 0

#get the data from arduino serial monitor
ser = serial.Serial("/dev/ttyACM0", 9600)
time.sleep(25)
test1 = str(ser.readline())
test1 = test1[2:-5]
test2 = str(ser.readline())
test2 = test2[2:-5]
test1Label = Label(root, text=test1)
#test1Label.grid(row=15)
test2Label = Label(root, text=test2)
#test2Label.grid(row=16)

#print the data
#results1 = test1.split(' ')
envTempText, envLightText, envResText = test1.split()
crystTempText, crystLightText, crystResText = test2.split() 

#values
#envTempText = "Обробка..."
#envLightText = "Обробка..."
#envResText = "Обробка..."
#crystTempText = "Обробка..."
#crystLightText = "Обробка..."
#crystResText = "Обробка..."
resHeatText = str(float(crystTempText) - float(envTempText))
resHeatText = resHeatText[:5]
resLightText = str(float(crystLightText) - float(envLightText))
resTypeText = "Будь ласка, повторіть дослід."
par = float(resLightText)

#convert values to calculate coefficients
if float(resHeatText) == 0:
	plast = abs(float(crystResText) / (float(resHeatText)+1)/1000)
else:
	plast = abs(float(crystResText) / (float(resHeatText))/10000) 	
#if plast < 0:
#	plast = plast*(-1) 
if float(resLightText) == 0:
	heat = abs(float(resHeatText) / (float(resLightText)+1) * 100)
else:
	heat = abs(float(resHeatText) / (float(resLightText)) * 100) 


#Find parameters
if par >= -200 and par < 0 or par > 0 and par < 50:
	resTypeText = "3 порядок"
elif par >= 50 and par < 90:
	resTypeText = "4 порядок"
elif par >= 90 and par < 300:
	resTypeText = "2 порядок"
#elif par >= 300 and par < 1023:
#	resTypeText = "5 порядок"
elif par >= 300 and par < 1023:
	resTypeText = "1 порядок"		


#labels for window
spaceLabel1 = Label(root, text="\n")
spaceLabel2 = Label(root, text="\n \n")
spaceLabel3 = Label(root, text="\n \n")
#environment parameters
envLabel = Label(root, text= "Робочі параметри:", font="Helvetica 13 bold")
envTempLabel = Label(root, text="=======Середовища:=======\nТемпература:     " + envTempText + " °C \nПрозорість:        " + envLightText + " ум.од.\nОпір датчика:     " + envResText + " ум.од.\n\n\n========Кристалу:========\nТемпература:     " + crystTempText +  "°C\nПрозорість:        " + crystLightText + " ум.од.\nОпір датчика:     " + crystResText + " ум.од.", font="Arial 12")
#envLightLabel = Label(root, text="Прозорість:        " + envLightText + " ум.од.", font="Arial 12")
#envResLabel = Label(root, text="Опір датчика:     " + envResText + " ум.од.", font="Arial 12")

spaceLabel1.grid(row=0)
envLabel.grid(row=1, sticky=W)
envTempLabel.grid(row=2, sticky=N)
#envLightLabel.grid(row=3, sticky=W)
#envResLabel.grid(row=4, sticky=W)
#spaceLabel2.grid(row=5)

#crystall parameters
#crystLabel = Label(root, text="Робочі параметри кристалу:", font="Helvetica 13 bold")
#crystTempLabel = Label(root, text="Температура:     " + crystTempText + " °C\nПрозорість:        " + crystLightText + " ум.од.\nОпір датчика:     " + crystResText + " ум.од.", font="Arial 12")
#crystLightLabel = Label(root, text="Прозорість:        " + crystLightText + " ум.од.", font="Arial 12")
#crystResLabel = Label(root, text="Опір датчика:     " + crystResText + " ум.од.", font="Arial 12")

#crystLabel.grid(row=3, sticky=W)
#crystTempLabel.grid(row=4, sticky=N)
#crystLightLabel.grid(row=8, sticky=W)
#crystResLabel.grid(row=9, sticky=W)
#spaceLabel3.grid(row=10)

#result parameters
resLabel = Label(root, text="Результати вимірювання:", font="Helvetica 13 bold")
resHeatLabel = Label(root, text="Різниця темп.:     " + resHeatText + " °C \nПрозорість:       " + resLightText + " ум.од.\n\n\n =======Порядок симетрії:=======\n\n\t    " + resTypeText + "\n\n Пластичність (p ум.) : " + str("%.2f" % plast) + "%\n Теплопоглинання (k% ум.): " + str("%.2f" % heat) + "%", font="Arial 12")
#resLightLabel = Label(root, text="Прозорість:     " + resLightText, font="Arial 12")
#resTypeLabel = Label(root, text="Тип гратки:     " + resTypeText, font="Arial 12")

resLabel.grid(row=3, sticky=W) 
resHeatLabel.grid(row=4, sticky=N)
#resLightLabel.grid(row=13, sticky=W)
#resTypeLabel.grid(row=14, sticky=W)

imageAn = an1
imageGeom = geom1 
if resTypeText == "1 порядок":
	imageAn = an1
	imageGeom = geom1 
elif resTypeText == "2 порядок":
	imageAn = an2 
	imageGeom = geom2 
elif resTypeText == "3 порядок":
	imageAn = an3 	
	imageGeom = geom3
elif resTypeText == "4 порядок":
	imageAn = an4 
	imageGeom = geom4
elif resTypeText == "5 порядок":
	imageAn = an5 
	imageGeom = geom5
elif resTypeText == "6 порядок":
	imageAn = an6
	imageGeom = geom6 				 				 			

anNLabel = Label(root, text="\tМожлива дифракція:", font="Helvetica 13 bold")
anLabel = Label(root, image=imageAn)
geomNLabel = Label(root, text="\tГеометрична інтерпретація:", font="Helvetica 13 bold")
geomLabel = Label(root, image=imageGeom)

anNLabel.grid(row=1, column=2)
anLabel.grid(row=2, column=2, sticky=E)
geomNLabel.grid(row=3, column=2)
geomLabel.grid(row=4, column=2, sticky=E)

def saveResults():
	file = open('results.txt', 'w')
	file.write("Параметри: \n=======Середовища:=======\nТемпература:     " + envTempText + " °C \nПрозорість:        " + envLightText + " ум.од.\nОпір датчика:     " + envResText + " ум.од.\n\n\n========Кристалу:========\nТемпература:     " + crystTempText +  "°C\nПрозорість:        " + crystLightText + " ум.од.\nОпір датчика:     " + crystResText + " ум.од.\n")
	file.write("\nРезультати: \nПрозорість:       " + resLightText + " ум.од.\n\n\n =======Порядок симетрії:=======\n\n\t    " + resTypeText + "\n\n Пластичність (p ум.) : " + str("%.2f" % plast) + "\n Теплопоглинання (k% ум.): " + str("%.2f" % heat) + "%")
	file.close()
	messagebox.showinfo('CrystallAnalyzer 1.0', 'Результати збережено.')

menu = Menu(root)
root.config(menu=menu)

subMenu = Menu(menu)
menu.add_cascade(label="Файл", menu=subMenu)
subMenu.add_command(label="Зберегти результати", command=saveResults)
subMenu.add_command(label="Вихід", command=root.quit)

helpMenu = Menu(menu)
menu.add_cascade(label="Довідка", menu=helpMenu)
aboutMenu = Menu(menu)
menu.add_cascade(label="Про програму", menu=aboutMenu)

root.mainloop()
