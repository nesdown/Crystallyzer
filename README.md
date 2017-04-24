# Crystallyzer
<i>Now crystallography is simple as never before.</i>

What for?
--------
This is a softwate part of a project made for physics experiments and analysis of crystalls. Allows to get full information about a crystall in simple and nice-looking form containing all measured parameters, etc. temperature, transparency, symmetry order, etc. Uses set of different forms for text messages, dialog menus, popups and image blocks.

How does it work?
-----------------
All the measurments gets into ATMega memory via sensors like thermistor, photoresistor, pressure sensor etc. Next part is converting data into SI measure values (all via hardware part) and sends them to the computer with SerialMonitor Connection Interface. Next step is comparing median values with database stored on client's machine and building UI with all measured values converted into understandable form.

Explain Simplier!
-----------------
There's some sort of step-by step algorithm:  

• Measurment     
   
• Converting data into SI    
    
• Sending values via Serial Monitor    
    
• "Scrapping" data from serial monitor with Python script (magic starts here!)    
    
• Comparing values with special database    
    
• Managing special UI window powered by TKinter framework      

How to launch?
--------------
Connect Arduino device (sketches coming soon!) with USB cable, open port access via Terminal if you're using Linux, launch an experiment with following command (make sure you have Python 3 installed)

<code>~/your-path$ python3 CrytallAnalyzer.py</code>

All the same for Windows. Complete all the measurement steps and wait for a while till results screen appears. Note that you can save results as a text document for next usage.

There are 6 symmetry orders supported: 0th, 2nd, 3rd, 4th, 6th and prohibited in classical crystallography 5th. All of them have geometric interpretation (Take a look at 'geometry' folder).
