import xml.etree.ElementTree as ET
tree = ET.parse('example.ghx')
root = tree.getroot()
print root.tag
print root.attrib
