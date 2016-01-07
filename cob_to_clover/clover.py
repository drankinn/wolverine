import lxml.etree as ET
import argparse
import pkg_resources

def convert(inxml):
    dom = ET.parse(inxml)
    xslt = ET.parse('cob_to_clover/transform.xslt')
    transform = ET.XSLT(xslt)
    newdom = transform(dom)
    return ET.tostring(newdom, pretty_print=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('coverage_xml')
    parser.add_argument('-o', '--output', required=False)
    args = parser.parse_args()
    converted = convert(args.coverage_xml)
    if args.output:
        with open(args.output, 'w') as out:
            out.write(converted.decode())
    else:
        print(converted)

if __name__ == '__main__':
  main()
