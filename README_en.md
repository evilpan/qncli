# qncli

`qncli` is a command line tool for QiNiu CDN service.
The command line interface is UNIX like. Just play with it!

```
$ ./qncli.py -h
usage: qncli [-h] [-c CONFIG] {ls,stat,mv,cp,rm,upload,fetch,edit} ...

QiNiu Command Line Interface

positional arguments:
  {ls,stat,mv,cp,rm,upload,fetch,edit}
                        available commands. qncli <command> -h to see more
                        help messages
    ls                  list remote files
    stat                show detail of remote file
    mv                  move file
    cp                  copy file
    rm                  remove file in remote bucket
    upload              upload local file to remote bucket
    fetch               fetch network file to remote bucket
    edit                edit network file MIME type and/or storage type

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        path to qiniu configuration. (default: conf/qiniu.json)
```

[![asciicast](https://asciinema.org/a/PNM6TXVYrRQxXO6e4oSUegCbS.png)](https://asciinema.org/a/PNM6TXVYrRQxXO6e4oSUegCbS)

## Example

upload local file to cloud:

    qncli.py upload /home/pan/screenshot.png

fetch nework file to cloud:

    qncli.py fetch "http://example.com/background.jpg" -d img/example.jpg

list files in cloud:

    qncli.py ls

show detail infomation of remote file:

    qncli.py stat screenshot.png

change MIME format of remote file:

    encli.py edit screenshot.png --mime 'text/plain'

move/rename remote file:

    qncli.py mv screenshot.png img/screenshot.png

delete remote file:

    qncli.py rm img/screenshot.png

## configuration

Configuration file should be placed in [conf/qncli.json](#),
please refer to [the example configuration](conf/example.json) for detail.
