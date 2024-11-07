import pandas as pd 
import openpyxl


data1=pd.read_csv(r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject\project\data\f1.csv')
data2=pd.read_csv(r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject\project\data\f2.csv')
data3=pd.read_csv(r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject\project\data\f3.csv')
data4=pd.read_csv(r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject\project\data\f4.csv')
data5=pd.read_csv(r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\datatrackAssignments\miniproject\project\data\f5.csv')
data2.to_excel(r'C:\Users\chvry\OneDrive\Desktop\New folder\data2.xlsx', index=False)

data3.to_json(r'C:\Data\db\data3.json',index=False)

data4.to_html(r'C:\Users\chvry\OneDrive\Desktop\data4.html', index=False)

data5.to_xml(r'C:\Users\chvry\OneDrive\Desktop\GUVI-CHUBB\data5.lxml', index=False)
