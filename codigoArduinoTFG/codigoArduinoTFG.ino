#include <TimerOne.h>
#include "SerialTransfer.h"
#include "DAC_MCP49xx.h"
#define INICIO 0XFFFF

//-----VARIABLES GLOBALES---------
DAC_MCP49xx dac(DAC_MCP49xx::MCP4921, 6); //Se declara el objeto dac, que controlará el DAC. Los parámetros son el modelo de DAC y el pin CS

SerialTransfer myTransfer;

uint16_t arr[581]; //Cada posición del array es una muestra de la señal
unsigned int posLectura = 0, posDAC = 0; //Punteros que marcan la muestra que se va almacenando(posLectura), y la muestra que se envía al DAC(posDAC)
uint16_t freqmuestreo; //Valor en microsegundos de la frecuencia de muestreo de cada señal
uint16_t nmuestras; //Número de muestras que se van a recibir
//--------------------------------

//-----RUTINA INTERRUPCIÓN TIMER-----
void salidaDAC(void)
{
  dac.output(arr[posDAC]);
  posDAC ++;
  
  if(posDAC > nmuestras){
    posDAC = 1;
  }
}
//-----------------------------------


void setup()
{
  Serial.begin(9600);
  myTransfer.begin(Serial);
  Timer1.initialize();
  memset(arr,0,sizeof(arr));  
}

void loop()
{ 
  if(myTransfer.available())
  {
    arr[posLectura] = (myTransfer.rxBuff[0] <<8) | myTransfer.rxBuff[1];
    
    if(arr[posLectura] == INICIO){
      nmuestras = (myTransfer.rxBuff[2] <<8) | myTransfer.rxBuff[3];
      freqmuestreo = (myTransfer.rxBuff[4] <<8) | myTransfer.rxBuff[5];
      Timer1.attachInterrupt(salidaDAC,freqmuestreo); // Se activa la salida del DAC a la frecuencia de muestreo de la señal 
      }

    posLectura ++;
    
    if(posLectura > nmuestras){
      posLectura = 1;
    }
    
    myTransfer.txBuff[0] = arr[posLectura] >>8;
    myTransfer.txBuff[1] = arr[posLectura];

    myTransfer.sendData(2);

  }
  else if(myTransfer.status < 0)
  {
    Serial.print("ERROR: ");
    Serial.println(myTransfer.status);
  }
}
