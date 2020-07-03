#TFG JESUS LAJARA CAMACHO

#Se importa el paquete wfdb para trabajar con la base de datos de physionet
import wfdb

#Se importa el paquete  serial, para iniciar la comunicación con arduino vía puerto serie
import serial

#Se importa el paquete tkinter para realizar la interfaz de usuario
from tkinter import *
#Se agrega el módulo combobox y el checkbutton, del módulo ttk
from tkinter.ttk import Combobox
from tkinter.ttk import Checkbutton

#Se añade la gráfica, para ello hay que importarla del paquete matplotlib
#Se importa también la toolbar, que añade funcionalidades a la gráfica
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
from matplotlib import style

#Se importa el módulo pySerialTransfer para la comunicación por el puerto serie con Arduino
from pySerialTransfer import pySerialTransfer as txfer

#Se importa la función sleep para esperar a que se abra el enlace con el puerto serie 
from time import sleep

#Se importa la función Thread del módulo threading para evitar que la interfaz gráfica se quede congelada
from threading import Thread

#--------VARIABLES GLOBALES---------------- 
muestraini=0 #Muestra inicial por defecto para la visualización
muestrafin=2000 #Muestra final por defecto para la visualización
envio=False #Variable que indica si hay que enviar la señal o solo visualizarla
textbbdd1="MIT-BIH Arrhythmia"
textbbdd2="European ST-T Database" #'ANSI/AAMI EC13 Test'
signalsbbdd1=['100','101','102','200','234'] 
signalsbbdd2=['e0103','e0104','e0105','e0106'] #['aami4a_d','aami3a','aami3b','aami3c','aami4a']
IDbbdd1='mitdb'
IDbbdd2='edb' #'aami-ec13' 
puertosUSB=[] #Lista que almacenará los puertos USB disponibles para la comunicación con Arduino
#--------FIN VARIABLES GLOBALES------------ 

style.use("seaborn") #estilo de la gráfica

figura = Figure(figsize=(8,4), dpi=100,tight_layout=True) #Se define la gráfica

window = Tk() #Se inicializa la interfaz de usuario
 
window.title("SIMULADOR DE PACIENTE") 
window.geometry('940x780') #ancho x alto
window.resizable(0,0) #bloquea la ventana para que no se pueda cambiar el tamaño
window.iconbitmap("icon.ico") #carga el logo de la ETSIT como icono de ventana
window.config(background="light cyan")

#Frame para la información del usuario
miFrame1=Frame(window)
miFrame1.configure(background="white",bd=5,relief="ridge")
miFrame1.pack(fill=X,pady=10,padx=10)

#Frame para la selección de bbdd y señal
miFrame2=Frame(window)
miFrame2.configure(bd=5,relief="raised")
miFrame2.pack(pady=10)

#Frame para el botón de seleccionar ventana de la señal y enviar señal
miFrame3=Frame(window)
miFrame3.configure(bd=5,relief="raised")
miFrame3.pack(pady=10)

#Frame para el botón de visualización de la señal y puerto serie
miFrame4=Frame(window)
miFrame4.configure(bd=5,relief="raised")
miFrame4.pack(pady=10)

#Frame para mostrar la gráfica seleccionada
miFrame5=Frame(window)
miFrame5.configure(background="white",bd=5,relief="ridge")
miFrame5.pack(padx=10)


#---------------------------------------------#
#-----------FUNCIONES DEL PROGRAMA------------#
#---------------------------------------------#

def cargaSignal():
    global envio
    estadoSelecc = revisaSeleccion()

    if(estadoSelecc == 0):
        return 0
    else:
        habilitaWidgets(labelsampto,entrysampto,labelsampfrom,entrysampfrom,botonmuestra)
        muestraini = int(entrysampfrom.get())
        muestrafin = int(entrysampto.get())

        if(estadoSelecc == 1):
            stringsignal = combo1.get()
            bbdd = IDbbdd1
        else:
            stringsignal = combo2.get()
            bbdd = IDbbdd2

        if(envio == False):
            infouser.set("Señal " + stringsignal + ". Seleccione la muestra inicial y final. Máx 580 muestras.")
        
        if (((muestrafin-muestraini)>580) and envio):
        	infouser.set("El número de muestras a enviar no puede superar 580. Modifique el valor.")
        	messagebox.showinfo('ERROR','Seleccione 580 muestras o menos')
        	return 0

        try:
        	ecg= wfdb.rdsamp(stringsignal,channels=[0],sampfrom=muestraini, sampto=muestrafin,pb_dir=bbdd)
        except ValueError:
        	infouser.set("Seleccione valores de inicio y fin de muestra válidos. Máx 580 muestras.")
        	messagebox.showinfo('ERROR','La muestra final debe ser mayor que la inicial y no se admiten números negativos')
        	return 0

        nmuestras=[j for j in range(muestrafin - muestraini)]
        a = figura.add_subplot(111)
        a.plot(nmuestras,ecg[0])
        a.set_ylabel('Voltaje (mV)')
        a.set_xlabel('Número de muestras')
        grafica.draw()
        
        if(envio):
            entrysampfrom.delete(0,4)
            entrysampfrom.insert(0,0)
            entrysampto.delete(0,4)
            entrysampto.insert(0,2000) #Se reinician los valores por defecto de visualización de la gráfica
            deshabilitaWidgets(labelsampto,entrysampto,labelsampfrom,entrysampfrom,botonmuestra)
            envio = False
            Thread(target=iniciaComunicacion(ecg)).start()
        else:
            deshabilitaWidgets(labelpuerto,comboPuertos,boton,titulo1,combo1,check1,titulo2,combo2,check2)
            envio = True

def mapeoTensiones(x, min_entrada, max_entrada, min_salida, max_salida):
    # Para un valor de x comprendido en el rango [min_entrada,max_entrada]
    # devuelve el valor que le corresponderia en el rango [min_salida,max_salida]
    return int((x-min_entrada) * (max_salida-min_salida) / (max_entrada-min_entrada) + min_salida)


def iniciaComunicacion(ecg):
    #Función que abre el enlace con el puerto serie y envía la señal de datos;

    mem=[] #Variable vacía para almacenar la respuesta de Arduino.

    try:
        
        link = txfer.SerialTransfer(comboPuertos.get()) #Seleccionar el puerto COM correspondiente a Arduino
        link.open() #Abrir el enlace con el puerto serie
        sleep(1)

        nmuestras = ecg[1]["sig_len"]
        nmuestrasSend = [nmuestras >> 8, nmuestras & 0xFF]

        freqmuestreo = int((1/ecg[1]["fs"])*1000000) #Esta línea muestra el valor en us de la freq de muestreo, necesario para inciar el timer del dac en arduino.
        freqSend = [freqmuestreo >> 8, freqmuestreo & 0xFF]

        link.txBuff[0] = 0xFF
        link.txBuff[1] = 0xFF
        link.txBuff[2] = nmuestrasSend[0]
        link.txBuff[3] = nmuestrasSend[1]
        link.txBuff[4] = freqSend[0]
        link.txBuff[5] = freqSend[1]
        link.send(6)

        for x in ecg[0]:
            valor = mapeoTensiones(x,min(ecg[0]),max(ecg[0]),0,4095) #Se convierte del rango de la señal al rango del DAC
            valorSend = [valor >> 8, valor & 0xFF] #Se cambia el formato a dos bytes en hexadecimal para enviarlos byte a byte

            link.txBuff[0] = valorSend[0]
            link.txBuff[1] = valorSend[1]
            link.send(2)

            while (not link.available()):
                if link.status < 0:
                    print('ERROR: {}'.format(link.status))
            for index in range(link.bytesRead):
                mem.append(hex(link.rxBuff[index])) #Se reciben los datos que envía Arduino
        link.close()

        infouser.set("Señal enviada con éxito. Seleccione otra señal o finalice el programa.")
        habilitaWidgets(labelpuerto,boton,titulo1,combo1,check1,titulo2,combo2,check2)

    except:
    	habilitaWidgets(boton,titulo1,combo1,check1,titulo2,combo2,check2)
    	infouser.set("Error en la comunicación.")


def habilitaWidgets(*widgets):
    for w in widgets:
        w.config(state=NORMAL)

def deshabilitaWidgets(*widgets):
    for w in widgets:
        w.config(state=DISABLED)

def revisaSeleccion():
    if((check1_state.get() and check2_state.get()) == True):
    	infouser.set("Seleccione solo una BBDD.")
    	messagebox.showinfo('ERROR','Solo puede seleccionar una BBDD')
    	figura.clf()
    	return 0

    elif((check1_state.get() or check2_state.get())==False):
    	infouser.set("Debe seleccionar una BBDD.")
    	messagebox.showinfo('ERROR','Seleccione una BBDD')
    	figura.clf()
    	return 0

    elif((check1_state.get()==True) and (check2_state.get()==False)):
        #BBDD de la izquierda en la interfaz
        figura.clf()
        return 1

    elif((check1_state.get()==False) and (check2_state.get()==True)):
        #BBDD de la derecha en la interfaz
        figura.clf()
        return 2
    if((int(entrysampfrom.get()) < 0) or (int(entrysampto.get()) > 9000) or (int(entrysampfrom.get()) > int(entrysampto.get())) ):
    	infouser.set("Seleccione valores de inicio y fin de muestra válidos.")
    	messagebox.showinfo('ERROR','Valores de inicio y fin de muestra incorrectos')
    	return 0

#---------------------------------------------#
#---------FIN FUNCIONES DEL PROGRAMA----------#
#---------------------------------------------#


#---------FRAME 1. INFORMACIÓN PARA EL USUARIO---------
etiqueta1=Label(miFrame1, text= "Información para el usuario: ", font=("Arial Bold",15),background="light grey",anchor=CENTER)
etiqueta1.grid(column=0,row=0)

infouser = StringVar() #variable string para mostrar la información de la ejecución del programa al usuario
infouser.set("Seleccione la base de datos, señal y puerto USB.")

etiqueta=Label(miFrame1,textvariable=infouser,font=("Arial",15),background="white",fg="blue")
etiqueta.grid(column=2,row=0,columnspan=4)
#------------------------------------------------------

#---------FRAME 2. SELECCIÓN DE LA BBDD Y LA SEÑAL---------
titulo1 = Label(miFrame2, text=textbbdd1, font=("Arial",15))
titulo1.grid(column=0,row=2,padx=35,pady=4)

combo1 = Combobox(miFrame2,state="readonly")
combo1['values']= signalsbbdd1
combo1.current(0) #Selecciona por defecto el primer valor
combo1.grid(column=0,row=3,padx=35)

check1_state = BooleanVar()
check1_state.set(False) #La casilla se muestra inicialmente desmarcada
check1 = Checkbutton(miFrame2, text="Elija esta BBDD", var=check1_state)
check1.grid(column=0, row=5,padx=35,pady=4)									

titulo2 = Label(miFrame2, text=textbbdd2, font=("Arial",15))
titulo2.grid(column=5,row=2,padx=31,pady=4)

combo2 = Combobox(miFrame2,state="readonly")
combo2['values']= signalsbbdd2
combo2.current(0) #Selecciona por defecto el primer valor
combo2.grid(column=5,row=3,padx=45)

check2_state = BooleanVar()
check2_state.set(False) #La casilla se muestra inicialmente desmarcada
check2 = Checkbutton(miFrame2, text="Elija esta BBDD", var=check2_state)
check2.grid(column=5, row=5,padx=45,pady=4)
#-----------------------------------------------------------

#---------FRAME 3. SELECCIÓN DE LA VENTANA DE LA SEÑAL Y BOTON DE ENVIO DE LA SEÑAL---------
labelsampfrom = Label(miFrame3,text="Muestra inicial: ",state=DISABLED)
labelsampfrom.pack(side=LEFT,padx=3,pady=2)

entrysampfrom = Entry(miFrame3,width=5)
entrysampfrom.insert(0,muestraini)
entrysampfrom.config(state=DISABLED)
entrysampfrom.pack(side=LEFT,padx=5,pady=2)

labelsampto = Label(miFrame3,text="Muestra final: ",state=DISABLED)
labelsampto.pack(side=LEFT,padx=5,pady=2)

entrysampto = Entry(miFrame3,width=5)
entrysampto.insert(0,muestrafin)
entrysampto.config(state=DISABLED)
entrysampto.pack(side=LEFT,padx=5,pady=2)

botonmuestra = Button(miFrame3,text="Envíe la señal a Arduino",state=DISABLED,command=cargaSignal)
botonmuestra.pack(side=RIGHT,padx=66,pady=2)
#-------------------------------------------------------------------------------------------

#---------FRAME 4. BOTÓN ENVÍO DE LA SEÑAL A LA GRÁFICA Y PUERTO SERIE---------
labelpuerto = Label(miFrame4,text="Escoja puerto Arduino: ")
labelpuerto.pack(side=LEFT)

puertosUSB=[]

try:
    for a in serial.tools.list_ports.comports():
    	puertosUSB.append(a[0])
    comboPuertos = Combobox(miFrame4,values=puertosUSB,width=15,state="readonly") #Estado readonly para no modificar la lista
    comboPuertos.current(0)
except:
    comboPuertos = Combobox(miFrame4,values=puertosUSB,state=DISABLED,width=10) #Estado deshabilitado
    messagebox.showinfo('ERROR','No se encuentra ninguna placa')
    infouser.set("Conecte una placa de desarrollo y reinicie la aplicación.")

comboPuertos.pack(side=LEFT)

boton = Button(miFrame4, text="Visualice la señal",command=cargaSignal)
boton.pack(side=RIGHT,padx=101,pady=2)
#------------------------------------------------------------------------------

#---------FRAME 5. VISUALIZACIÓN DE LA GRÁFICA------------------
#Se muestra la gráfica
grafica = FigureCanvasTkAgg(figura,miFrame5)
grafica.draw()
grafica.get_tk_widget().pack(side=TOP,expand=True)

#Se muestra la toolbar de la gráfica
toolbar = NavigationToolbar2Tk(grafica, miFrame5)
toolbar.update()
grafica._tkcanvas.pack(side=TOP,expand=True)
#---------------------------------------------------------------

Thread(target=window.mainloop()).start() #FUNCIÓN NECESARIA PARA INICAR LA INTERFAZ GRÁFICA