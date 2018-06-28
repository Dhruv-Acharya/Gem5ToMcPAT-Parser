# Gem5 to McPAT parser with multicore support



This Script converts Gem5 simulation statistics to McPAT compatible input files. It supports multiple cores as well as multiple private or one shared L2 cache



### Usage

Parser requires [python 2.7](https://www.python.org/download/releases/2.7/) to run.



```sh
 usage: Gem5ToMcPAT-Parser.py [-h] --config PATH --stats PATH --template PATH
                                    [--output PATH]

        Gem5 to McPAT parser

        optional arguments:
        -h, --help            show this help message and exit
        --config PATH, -c PATH
                                Input config.json from Gem5 output.
        --stats PATH, -s PATH
                                Input stats.txt from Gem5 output.
        --template PATH, -t PATH
                                Template XML file
        --output PATH, -o PATH
                                Output file for McPAT input in XML format (default:
                                mcpat-in.xml)
```

### Example

```sh
$ python Gem5ToMcPAT-Parser.py -c config.json -s stats.txt -t template.xml
```


License
----

MIT

### Credits

It uses some of the work from a different author:

* [Daya Khudia] - template and some functions has been derived from this repository and updated

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)


   
   [Daya Khudia]: <https://bitbucket.org/dskhudia/gem5tomcpat/>

