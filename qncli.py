#!/usr/bin/env python3
import os
import logging
import argparse
import json
from datetime import datetime
import qiniu
from qiniu import zone

def readable_size(number_of_bytes):
    if number_of_bytes < 0:
        return number_of_bytes
    units = ['K', 'M', 'G', 'T']
    step = 1024
    unit = ''
    display = number_of_bytes
    for i in range(len(units) + 1):
        if (display / step < 1):
            break
        display /= step
        unit = units[i]
    display = round(display, 1)
    return str(display) + unit

class QiniuManager(object):
    DEFAULT_PROTOCOL = 'http'
    DEFAULT_DOMAIN = 'www.yourdomain.com'
    DEFAULT_BUCKET = 'your_bucket_name'
    def __init__(self, *args, **kwargs):
        formater = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formater)
        self.loglevel = kwargs.pop('loglevel', 'INFO')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.loglevel)
        self.logger.addHandler(handler)

        self.logger.debug('config: {}'.format(kwargs))
        self.access_key = kwargs.pop('access_key')
        self.secret_key = kwargs.pop('secret_key')
        if not self.access_key or not self.secret_key:
            raise ValueError('access_key and secret_key is required')
        self.buckets = kwargs.pop('buckets', [])
        if len(kwargs) != 0:
            self.logger.warn('unknown kwargs: {}'.format(kwargs))
        self.zone = zone.Zone(home_dir='/tmp')
        self.auth = qiniu.Auth(self.access_key, self.secret_key)
        self.bucket_manager = qiniu.BucketManager(self.auth, zone=self.zone)

    @property
    def default_bucket(self):
        bucket = {
                'name': self.DEFAULT_BUCKET,
                'domain': self.DEFAULT_DOMAIN,
                'protocol': self.DEFAULT_PROTOCOL,
                'private': False
                }
        if len(self.buckets) == 0:
            bucket
        return self.buckets[0]

    @property
    def default_bucket_name(self):
        return self.default_bucket.get('name', self.DEFAULT_BUCKET)

    def print_buckets(self):
        for bucket in self.buckets:
            print('{:10s}{:10s}\t{}://{}'.format(bucket['name'],
                'private' if bucket['private'] else 'public',
                 bucket['protocol'], bucket['domain']))

    def _handle_error(self, ret, info, command='Qiniu'):
        self.logger.error('{} failed: ({}){}'.format(command, info.status_code, info.error))
        self.logger.debug('{} failed, info:{}'.format(command, info))

    def _get_url(self, bucket_name, remote_file):
        bucket = self.default_bucket
        for b in self.buckets:
            if b['name'] == bucket_name:
                bucket = b
                break
        base_url = '{}://{}/{}'.format(bucket['protocol'], bucket['domain'], remote_file)
        if bucket['private']:
            return self.auth.private_download_url(base_url, expires=3600)
        else:
            return base_url

    def stat(self, remote_file, bucket_name=''):
        bucket_name = bucket_name or self.default_bucket_name
        ret, info = self.bucket_manager.stat(bucket_name, remote_file)
        self.logger.debug('stat ret: {}'.format(ret))
        if not info.ok():
            self._handle_error(ret, info, 'stat')
            return False
        msg = ''
        msg += 'PATH: {}\n'.format(remote_file)
        msg += ' URL: {}\n'.format(self._get_url(bucket_name, remote_file))
        msg += 'SIZE: {} bytes\n'.format(ret['fsize'])
        msg += 'TYPE: {}({})\n'.format(ret['type'], 'standard' if ret['type'] == 0 else 'low frequency')
        msg += 'TIME: {}\n'.format(datetime.fromtimestamp(ret['putTime']/10000000).strftime('%Y-%m-%d %H:%M:%S'))
        msg += 'MIME: {}\n'.format(ret['mimeType'])
        msg += 'HASH: {}\n'.format(ret['hash'])
        self.logger.info('stat result of [{}] {}:\n{}'.format(
            bucket_name, remote_file, msg))
        return True

    def list(self, prefix=None, limit=30, bucket_name='', **kwargs):
        """List files in remote bucket
        :param prefix: file prefix in bucket
        :param limit: max results
        :param bucket: bucket name
        :param kwargs delimiter: 指定目录分隔符，列出所有公共前缀（模拟列出目录效果）。默认值为空字符串。
        :param kwargs marker: 上一次列举返回的位置标记，作为本次列举的起点信息。默认值为空字符串。
        """
        bucket_name = bucket_name or self.default_bucket_name
        delimiter = kwargs.pop('delimiter', None)
        marker = kwargs.pop('marker', None)
        ret, eof, info = self.bucket_manager.list(bucket_name, prefix, marker, limit, delimiter)
        self.logger.debug('list ret: {}'.format(ret))
        if not info.ok():
            self._handle_error(ret, info, 'list')
            return False
        new_marker = ret.get('marker', '')
        items = ret.get('items', [])
        self.logger.info('[{}] matched {}{} item(s):'.format(
            bucket_name, len(items), '' if eof else '+'))
        for item in items:
            file_name = item.get('key')
            file_type = item.get('mimeType', 'N/A')
            file_size = item.get('fsize', -1)
            file_time = item.get('putTime', 0)
            print('{:>10s} {:<17s} {}  {}'.format(
                readable_size(file_size), file_type,
                datetime.fromtimestamp(file_time/10000000).strftime('%Y-%m-%d %H:%M'),
                file_name))
        if not eof:
            print('...Use --marker "{}" to see the rest results'.format(new_marker))
        return True

    def move(self, src, dst, src_bucket='', dst_bucket=''):
        src_bucket = src_bucket or self.default_bucket_name
        dst_bucket = dst_bucket or src_bucket
        ret, info = self.bucket_manager.move(src_bucket, src, dst_bucket, dst)
        if not info.ok():
            self._handle_error(ret, info, 'move')
            return False
        self.logger.info('moved [{}] {} to [{}] {}'.format(src_bucket, src, dst_bucket, dst))
        return True

    def copy(self, src, dst, src_bucket='', dst_bucket=''):
        src_bucket = src_bucket or self.default_bucket_name
        dst_bucket = dst_bucket or src_bucket
        ret, info = self.bucket_manager.copy(src_bucket, src, dst_bucket, dst)
        if not info.ok():
            self._handle_error(ret, info, 'copy')
            return False
        self.logger.info('copied [{}] {} to [{}] {}'.format(src_bucket, src, dst_bucket, dst))
        return True

    def remove_one(self, remote_file, bucket_name=''):
        bucket_name = bucket_name or self.default_bucket_name
        ret, info = self.bucket_manager.delete(bucket_name, remote_file)
        if not info.ok():
            self._handle_error(ret, info, 'remove')
            return False
        self.logger.info('deleted [{}] {}'.format(bucket_name, remote_file))
        return True

    def remove_many(self, remote_files, bucket_name=''):
        from qiniu import build_batch_delete
        bucket_name = bucket_name or self.default_bucket_name
        ops = build_batch_delete(bucket_name, remote_files)
        ret, info = self.bucket_manager.batch(ops)
        if not info.ok():
            self._handle_error(ret, info, 'remove')
            return False
        self.logger.info('deleted [{}] {}'.format(bucket_name, ', '.join(remote_files)))
        return True

    def upload(self, local_file, remote_file='', bucket_name=''):
        remote_file = remote_file or os.path.basename(local_file)
        bucket_name = bucket_name or self.default_bucket_name
        self.logger.info('Uploading "{}" to bucket "{}".'.format(remote_file, bucket_name))
        token = self.auth.upload_token(bucket_name, remote_file)
        ret, info = qiniu.put_file(token, remote_file, local_file)
        self.logger.debug('Upload ret: {}'.format(ret))
        if not info.ok():
            self._handle_error(ret, info, 'upload')
            return False
        self.logger.info('Upload done. url is ' + self._get_url(bucket_name, remote_file))
        return True

    def fetch(self, url, remote_file=None, bucket_name=''):
        bucket_name = bucket_name or self.default_bucket_name
        self.logger.debug('Fetching from {} to [{}] {}'.format(url, bucket_name, remote_file))
        ret, info = self.bucket_manager.fetch(url, bucket_name, remote_file)
        if not info.ok():
            self._handle_error(ret, info, 'fetch')
            return False
        self.logger.info('Fetche success to [{}] {} ({}).'.format(bucket_name,
            ret.get('key'), ret.get('mimeType')))
        return True

    def change_mime(self, remote_file, new_mime, bucket_name=''):
        """
        :param new_mime: MIME type string. example: 'text/html'
        """
        bucket_name = bucket_name or self.default_bucket_name
        ret, info = self.bucket_manager.change_mime(bucket_name, remote_file, new_mime)
        if not info.ok():
            self._handle_error(ret, info, 'change_mime')
            return False
        self.logger.info('Change [{}] {} type to {}'.format(bucket_name, remote_file, new_mime));
        return True

    def change_type(self, remote_file, new_type, bucket_name=''):
        """
        :param new_type: 0:标准存储； 1:低频存储
        """
        bucket_name = bucket_name or self.default_bucket_name
        ret, info = self.bucket_manager.change_type(bucket_name, remote_file, new_type)
        if not info.ok():
            self._handle_error(ret, info, 'change_type')
            return False
        self.logger.info('Change [{}] {} type to {}'.format(bucket_name, remote_file, new_type));
        return True

def main():
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'conf/qncli.json')

    parser = argparse.ArgumentParser(description='QiNiu Command Line Interface', prog='qncli')
    parser.add_argument('-c', '--config', default=config_path, help='path to qiniu configuration. (default: %(default)s)')
    subparsers = parser.add_subparsers(dest='command', help='available commands. qncli <command> -h to see more help messages')

    parser_buckets = subparsers.add_parser('buckets', help='list buckets')

    parser_list = subparsers.add_parser('ls', help='list remote files')
    parser_list.add_argument('-l', action='store_true', help='use a long listing format')
    parser_list.add_argument('-m', '--max', type=int, default=30, help='max files to list. (default: %(default)s)')
    parser_list.add_argument('--delimiter', default=None, help='delimiter used by qiniu')
    parser_list.add_argument('--marker', default=None, help='marker used by qiniu')
    parser_list.add_argument('prefix', nargs='?', help='list matching prefix')

    parser_stat = subparsers.add_parser('stat', help='show detail of remote file')
    parser_stat.add_argument('file_name', help='remote file_name with full path')

    parser_move = subparsers.add_parser('mv', help='move file')
    parser_move.add_argument('--src-bucket', default='', help='the bucket_name contains source file')
    parser_move.add_argument('src', help='source file path')
    parser_move.add_argument('--dst-bucket', default='', help='the bucket_name contains destination file')
    parser_move.add_argument('dst', help='destination file path')

    parser_copy = subparsers.add_parser('cp', help='copy file')
    parser_copy.add_argument('--src-bucket', default='', help='the bucket_name contains source file')
    parser_copy.add_argument('src', help='source file path')
    parser_copy.add_argument('--dst-bucket', default='', help='the bucket_name contains destination file')
    parser_copy.add_argument('dst', help='destination file path')

    parser_remove = subparsers.add_parser('rm', help='remove file in remote bucket')
    parser_remove.add_argument('file_name', nargs='+', help='remote files with full path')

    parser_upload = subparsers.add_parser('upload', help='upload local file to remote bucket')
    parser_upload.add_argument('-d', '--dest', default='', help='specify a different remote file_name')
    parser_upload.add_argument('file_name', help='local file_name with full path')

    parser_fetch = subparsers.add_parser('fetch', help='fetch network file to remote bucket')
    parser_fetch.add_argument('-d', '--dst', default=None, help='remote file fullpath. (default: hash(file))')
    parser_fetch.add_argument('url', help='network resource url')

    parser_edit = subparsers.add_parser('edit', help='edit network file MIME type and/or storage type')
    parser_edit.add_argument('file_name', help='remote file fullpath.')
    parser_edit.add_argument('-t', '--type', type=int, choices=[0, 1], help='storage type. 0: standard, 1: low frequence')
    parser_edit.add_argument('-m', '--mime', type=str, help='MIME type')

    # common argument
    for sub_parser in [parser_list, parser_stat, parser_remove,
            parser_upload, parser_fetch, parser_edit]:
        sub_parser.add_argument('-b', '--bucket', default='', help='remote bucket name. (default: %s)' % QiniuManager.DEFAULT_BUCKET)

    args = parser.parse_args()
    #print(args)
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
            qm = QiniuManager(**config)

    if args.command == 'buckets':
        qm.print_buckets()
    elif args.command == 'ls':
        qm.list(prefix=args.prefix, limit=args.max, bucket_name=args.bucket,
                delimiter=args.delimiter, marker=args.marker)
    elif args.command == 'stat':
        qm.stat(args.file_name, bucket_name=args.bucket)
    elif args.command == 'mv':
        qm.move(args.src, args.dst, args.src_bucket, args.dst_bucket)
    elif args.command == 'cp':
        qm.copy(args.src, args.dst, args.src_bucket, args.dst_bucket)
    elif args.command == 'rm':
        qm.remove_many(args.file_name, bucket_name=args.bucket)
    elif args.command == 'upload':
        qm.upload(args.file_name, remote_file=args.dest, bucket_name=args.bucket)
    elif args.command == 'fetch':
        qm.fetch(args.url, args.dst, bucket_name=args.bucket)
    elif args.command == 'edit':
        if args.type is not None:
            qm.change_type(args.file_name, args.type, bucket_name=args.bucket)
        if args.mime is not None:
            qm.change_mime(args.file_name, args.mime, bucket_name=args.bucket)
    else:
        print('Unknown command {}'.format(args.command))

if __name__ == '__main__':
    main()
