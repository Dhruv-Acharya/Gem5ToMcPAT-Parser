import argparse
import sys
import json
import re
from xml.etree import ElementTree as ET
from xml.dom import minidom
import copy
import types

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_parser():
    parser = argparse.ArgumentParser(
        formatter_class = argparse.RawDescriptionHelpFormatter,
        description = "Gem5 to McPAT parser")

    parser.add_argument(
        '--config', '-c', type = str, required = True,
        metavar = 'PATH',
        help = "Input config.json from Gem5 output.")
    parser.add_argument(
        '--stats', '-s', type = str, required = True,
        metavar = 'PATH',
        help = "Input stats.txt from Gem5 output.")
    parser.add_argument(
        '--template', '-t', type = str, required = True,
        metavar = 'PATH',
        help = "Template XML file")
    parser.add_argument(
        '--output', '-o', type = argparse.FileType('w'), default = "mcpat-in.xml",
        metavar = 'PATH',
        help = "Output file for McPAT input in XML format (default: mcpat-in.xml)")
    
    return parser

class PIParser(ET.XMLTreeBuilder):
   def __init__(self):
       ET.XMLTreeBuilder.__init__(self)
       # assumes ElementTree 1.2.X
       self._parser.CommentHandler = self.handle_comment
       self._parser.ProcessingInstructionHandler = self.handle_pi
       self._target.start("document", {})

   def close(self):
       self._target.end("document")
       return ET.XMLTreeBuilder.close(self)

   def handle_comment(self, data):
       self._target.start(ET.Comment, {})
       self._target.data(data)
       self._target.end(ET.Comment)

   def handle_pi(self, target, data):
       self._target.start(ET.PI, {})
       self._target.data(target + " " + data)
       self._target.end(ET.PI)

def parse(source):
    return ET.parse(source, PIParser())

def readStatsFile(statsFile):
    global stats
    stats = {}
    F = open(statsFile)
    ignores = re.compile(r'^---|^$')
    statLine = re.compile(r'([a-zA-Z0-9_\.:-]+)\s+([-+]?[0-9]+\.[0-9]+|[-+]?[0-9]+|nan|inf)')
    count = 0 
    for line in F:
        #ignore empty lines and lines starting with "---"  
        if not ignores.match(line):
            count += 1
            statKind = statLine.match(line).group(1)
            statValue = statLine.match(line).group(2)
            if statValue == 'nan':
                print "\tWarning (stats): %s is nan. Setting it to 0" % statKind
                statValue = '0'
            stats[statKind] = statValue
    F.close()

def readConfigFile(configFile):
    global config
    F = open(configFile)
    config = json.load(F)
    #print config
    #print config["system"]["membus"]
    #print config["system"]["cpu"][0]["clock"]
    F.close()

def readMcpatFile(templateFile):
    global templateMcpat 
    templateMcpat = parse(templateFile)
    #ET.dump(templateMcpat)

def prepareTemplate(outputFile):
    numCores = len(config["system"]["cpu"])
    numL2 = numCores
    elemCounter = 0
    root = templateMcpat.getroot()
    for child in root[0][0]:
        elemCounter += 1 # to add elements in correct sequence

        if child.attrib.get("name") == "number_of_cores":
            child.attrib['value'] = str(numCores)
        if child.attrib.get("name") == "number_of_L2s":
            child.attrib['value'] = str(numL2)
        temp = child.attrib.get('value')

        # to consider all the cpus in total cycle calculation
        if isinstance(temp, basestring) and "cpu." in temp and temp.split('.')[0] == "stats":
            value = "(" + temp.replace("cpu.", "cpu0.") + ")"
            for i in range(1, numCores):
                value = value + " + (" + temp.replace("cpu.", "cpu"+str(i)+".") +")"
            child.attrib['value'] = value

        # remove a core template element and replace it with number of cores template elements
        if child.attrib.get("name") == "core":
            coreElem = copy.deepcopy(child)
            coreElemCopy = copy.deepcopy(coreElem)
            for coreCounter in range(numCores):
                coreElem.attrib["name"] = "core" + str(coreCounter)
                coreElem.attrib["id"] = "system.core" + str(coreCounter)
                for coreChild in coreElem:
                    childId = coreChild.attrib.get("id")
                    childValue = coreChild.attrib.get("value")
                    if isinstance(childId, basestring) and "core" in childId:
                        childId = childId.replace("core", "core" + str(coreCounter))
                    if isinstance(childValue, basestring) and "cpu." in childValue and "stats" in childValue.split('.')[0]:
                        childValue = childValue.replace("cpu." , "cpu" + str(coreCounter)+ ".")
                    if isinstance(childValue, basestring) and "cpu." in childValue and "config" in childValue.split('.')[0]:
                        childValue = childValue.replace("cpu." , "cpu." + str(coreCounter)+ ".")
                    if len(list(coreChild)) is not 0:
                        for level2Child in coreChild:
                            level2ChildValue = level2Child.attrib.get("value")
                            if isinstance(level2ChildValue, basestring) and "cpu." in level2ChildValue and "stats" in level2ChildValue.split('.')[0]:
                                level2ChildValue = level2ChildValue.replace("cpu." , "cpu" + str(coreCounter)+ ".")
                            if isinstance(level2ChildValue, basestring) and "cpu." in level2ChildValue and "config" in level2ChildValue.split('.')[0]:
                                level2ChildValue = level2ChildValue.replace("cpu." , "cpu." + str(coreCounter)+ ".")
                            level2Child.attrib["value"] = level2ChildValue
                    if isinstance(childId, basestring):
                        coreChild.attrib["id"] = childId
                    if isinstance(childValue, basestring):
                        coreChild.attrib["value"] = childValue
                root[0][0].insert(elemCounter, coreElem)
                coreElem = copy.deepcopy(coreElemCopy)
                elemCounter += 1
            root[0][0].remove(child)
            elemCounter -= 1

        # remove a L2 template element and replace it with number of L2 template elements
        if child.attrib.get("name") == "L2":
            l2Elem = copy.deepcopy(child)
            l2ElemCopy = copy.deepcopy(l2Elem)
            for l2Counter in range(numL2):
                l2Elem.attrib["name"] = "L2" + str(l2Counter)
                l2Elem.attrib["id"] = "system.L2" + str(l2Counter)
                for l2Child in l2Elem:
                    childValue = l2Child.attrib.get("value")
                    if isinstance(childValue, basestring) and "cpu." in childValue and "stats" in childValue.split('.')[0]:
                        childValue = childValue.replace("cpu." , "cpu" + str(l2Counter)+ ".")
                    if isinstance(childValue, basestring) and "cpu." in childValue and "config" in childValue.split('.')[0]:
                        childValue = childValue.replace("cpu." , "cpu." + str(l2Counter)+ ".")
                    if isinstance(childValue, basestring):
                        l2Child.attrib["value"] = childValue
                root[0][0].insert(elemCounter, l2Elem)
                l2Elem = copy.deepcopy(l2ElemCopy)
                elemCounter += 1
            root[0][0].remove(child)

            # for i in range(numCores):
            # for core in list(child.iter()):
            #     temp = core.attrib.get('value')
            #     if isinstance(temp, basestring) and "cpu." in temp and temp.split('.')[0] == "stats":
            # value = "(" + temp.replace("cpu.", "cpu0.") + ")"
            # for i in range(1, numCores):
            #     value = value + " + (" + temp.replace("cpu.", "cpu"+str(i)+".") +")"
            # child.attrib['value'] = value
            # print child.attrib.get("value")
    prettify(root)
    #templateMcpat.write(outputFile)

def getConfValue(confStr):
    spltConf = re.split('\.', confStr)
    currConf = config
    currHierarchy = ""
    for x in spltConf:
        currHierarchy += x
        if x.isdigit():
            currConf = currConf[int(x)] 
        elif x in currConf:
            # if isinstance(currConf, types.ListType):
            #     #this is mostly for system.cpu* as system.cpu is an array
            #     #This could be made better
            #     if x not in currConf[0]:
            #         print "%s does not exist in config" % currHierarchy 
            #     else:
            #         currConf = currConf[0][x]
            # else:
            #         print "***WARNING: %s does not exist in config.***" % currHierarchy 
            #         print "\t Please use the right config param in your McPAT template file"
        # else:
            currConf = currConf[x]
        currHierarchy += "."
    return currConf

# def getConfValue(confStr):
#     spltConf = re.split('\.', confStr)
#     currConf = config
#     for index in spltConf:
#         currConf = currConf[index]
#     return currConf

def dumpMcpatOut(outFile):
    rootElem = templateMcpat.getroot()
    configMatch = re.compile(r'config\.([][a-zA-Z0-9_:\.]+)')
    #replace params with values from the GEM5 config file 
    for param in rootElem.iter('param'):
        name = param.attrib['name']
        value = param.attrib['value']
        if 'config' in value:
            allConfs = configMatch.findall(value)
            for conf in allConfs:
                confValue = getConfValue(conf)
                value = re.sub("config."+ conf, str(confValue), value)
            if "," in value:
                exprs = re.split(',', value)
                for i in range(len(exprs)):
                    exprs[i] = str(eval(exprs[i]))
                param.attrib['value'] = ','.join(exprs)
            else:
                param.attrib['value'] = str(eval(str(value)))

    #replace stats with values from the GEM5 stats file 
    statRe = re.compile(r'stats\.([a-zA-Z0-9_:\.]+)')
    for stat in rootElem.iter('stat'):
        name = stat.attrib['name']
        value = stat.attrib['value']
        if 'stats' in value:
            allStats = statRe.findall(value)
            expr = value
            for i in range(len(allStats)):
                if allStats[i] in stats:
                    expr = re.sub('stats.%s' % allStats[i], stats[allStats[i]], expr)
                else:
                    print "***WARNING: %s does not exist in stats***" % allStats[i]
                    print "\t Please use the right stats in your McPAT template file"

            if 'config' not in expr and 'stats' not in expr:
                stat.attrib['value'] = str(eval(expr))
    #Write out the xml file
    templateMcpat.write(outFile)            

def main():
    global args
    parser = create_parser()
    args = parser.parse_args()
    readStatsFile(args.stats)
    readConfigFile(args.config)
    readMcpatFile(args.template)
    prepareTemplate(args.output)
    dumpMcpatOut(args.output)

if __name__ == '__main__':
    main()