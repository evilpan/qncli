# qncli

[README(English Version)](README_en.md)

`qncli`是七牛云存储的命令行封装, 使用类似`ls`,`stat`,`mv`,`cp`,`rm`等命令来方便快捷地管理云空间.

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

## 使用示例

上传本地文件到云空间:

    qncli.py upload /home/pan/screenshot.png

上传网络文件到云空间:

    qncli.py fetch "http://example.com/background.jpg" -d img/example.jpg

查看云空间的所有文件:

    qncli.py ls

查看云空间以`image`为前缀的文件:

    qncli.py ls image

查看文件详细信息:

    qncli.py stat screenshot.png

修改文件MIME格式:

    encli.py edit screenshot.png --mime 'text/plain'

移动/重命名空间文件:

    qncli.py mv screenshot.png img/screenshot.png

删除文件:

    qncli.py rm img/screenshot.png

## 配置

七牛的 `access_key/secret_key`等配置在`conf/qncli.json`文件中,
可以参考[conf/example.json](conf/example.json)
