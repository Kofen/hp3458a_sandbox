# hp3458a_sandbox
Misc scripts used for HP3458a testing/logging etc.

sn18_single3458.py is from xdevs.com: 
https://xdevs.com/guide/life_with_3458/
I have modified it to use my type of file formatting and to use Prologix(but with my library), this will probably not work out of the box for anyone else.
Xdevs is a must read for any owner of 3458a or voltnuts, fantastic resource!!

plot_sn18.py plot the resulting file, both my formatting and Xdevs so it is compatible with both styles. Specify tempco with --tempco or calculate it automatically with --auto_tempco. 
Be warned that for auto_tempco to work you need a sufficiently large dataset.

