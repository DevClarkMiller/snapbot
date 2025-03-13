import xml.etree.ElementTree as ET

def getNodesAttrib(root, attribs):
    for node in root:
        if 'package' not in node.attrib:
            continue
        if node.attrib['package'] == 'com.snapchat.android':
            vals = [node.attrib[att].strip() for att in attribs]
            print(vals)

if __name__ == "__main__":
    tree = ET.parse('dump.xml')
    root = tree.getroot()

    nodesAttrs = getNodesAttrib(root.findall('.//'), ['content-desc', 'text', 'bounds'])
    print(nodesAttrs)