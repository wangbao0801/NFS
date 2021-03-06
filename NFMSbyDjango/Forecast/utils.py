# coding: utf-8

import paramiko
import re
from time import sleep
import ftplib
from ftplib import FTP
import sys
import os
from NFMSbyDjango import settings
from Forecast import models

class ParamikoClient(object):
    def __init__(self ,ip, username, password,port=22, timeout=30):
        self.ip = ip
        self.username = username
        self.password = password
        self.port=port
        self.timeout = timeout

        self.client = None
        self.channel=None
        # 链接失败的重试次数
        self.try_times = 3

    def __connect(self):
        '''
        通过Paramiko进行连接
        :return:
        '''
        while True:
            # 连接过程中可能会抛出异常，比如网络不通、链接超时
            try:
                if self.client is None:                    
                    self.client = paramiko.SSHClient()
                    self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    self.client.connect(self.ip, self.port, self.username, self.password)
                    #开启频道
                    self.channel = self.client.invoke_shell()
                    # 如果没有抛出异常说明连接成功，直接返回
                    print(u'连接%s成功' % self.ip)
                    return
            # 这里不对可能的异常如socket.error, socket.timeout细化，直接一网打尽
            except Exception as e:
                if self.try_times != 0:
                    print(e)
                    print(u'连接%s失败，进行重试' % self.ip)
                    self.try_times -= 1
                else:
                    print(u'重试3次失败，结束程序')
                    return

    def __close(self):
        '''
        关闭Paramiko创建的连接
        :return:
        '''
        if self.client is not None:
            self.client.close()
            self.client=None

    def exec_cmd(self, cmd):
        '''
        执行命令
        :param cmd:
        :return:
        '''
        if self.client is None:
            self.__connect()
        stdin, stdout, stderr = self.client.exec_command(cmd)
        print(stdout.readlines())
        self.__close()

    def exec_shell(self,cmd):
        '''
        远程执行shell
        :param cmd:
        :return:返回结果
        '''
        recv_info = models.RecvResultInfo(0, "uninitialized")
        if self.channel is None:
            self.__connect()
        if self.channel is not None:
            re_match = '(\[.+?@.+?\s.+?\]\$)'
            self.channel.send(cmd + '\n')

            while True:
                '''
                由于执行完命令之后会以[lingtj@tlogin ~]$ 结尾
                eg：
                (0)	====20130401  08
                     warning:smth9: No missing values are being set.
                     .......................

                    (0)	---------- 006 Hours ------------
                        warning:NumVectors is not a valid resource in wbar_vector at this time

                     rasttopnm: writing PPM file
                     pamtogif: computing colormap...
                     pamtogif: 3 colors fou
                     nd
                        + '[' -n test17101703.gif ']'
                        + mv wbar.gif test17101703.gif
                    [lingtj@tlogin ~]$ 
            ************************************************
                若执行完命令总是以[lingtj@tlogin ~]$结束

                需要对[lingtj@tlogin ~]$进行匹配
                [除“\n”之外的任何单个字符出现一次或多次 @ 多个任意字符 空格 多个任意字符]$
                            '''
                # 将返回的receive data进行接收（二进制）——>转换为utf-8格式
                out = self.channel.recv(1024).decode('utf-8')
                print(out)
                # 匹配投
                result_match = re.findall(re_match, out)
                '''
                .strip()移除字符串头尾指定的字符（默认为空格）。
                .endswith() 方法用于判断字符串是否以指定后缀结尾，如果以指定后缀结尾返回True，否则返回False。可选参数"start"与"end"为检索字符串的开始与结束位置。
                '''
                # 有匹配结果并且该匹配结果出现在最后
                # 再跳出循环
                if result_match and out.strip().endswith(result_match[-1]):
                    self.__close()
                    recv_info.code=1
                    recv_info.result="ok"
                    # recv_info.
                    # return recv_info
                    break
        return recv_info




# 定义一个类，表示一台远端linux主机
class Linux(object):
    '''
    通过IP, 用户名，密码，超时时间初始化一个远程Linux主机
    '''
    def __init__(self, ip, username, password,port=22, timeout=30):
        self.ip = ip
        self.username = username
        self.password = password
        self.port=port
        self.timeout = timeout
        # transport和chanel
        self.t = ''
        self.chan = ''
        # 链接失败的重试次数
        self.try_times = 3


    # 调用该方法连接远程主机
    def connect(self):
        while True:
            # 连接过程中可能会抛出异常，比如网络不通、链接超时
            try:
                self.t = paramiko.Transport(sock=(self.ip, 22))
                self.t.connect(username=self.username, password=self.password)
                self.chan = self.t.open_session()
                self.chan.settimeout(self.timeout)
                self.chan.get_pty()
                self.chan.invoke_shell()
                # 如果没有抛出异常说明连接成功，直接返回
                print(u'连接%s成功' % self.ip)
                # 接收到的网络数据解码为str
                print(self.chan.recv(65535).decode('utf-8'))
                return
            # 这里不对可能的异常如socket.error, socket.timeout细化，直接一网打尽
            except Exception as e:
                if self.try_times != 0:
                    print(e)
                    print(u'连接%s失败，进行重试' %self.ip)
                    self.try_times -= 1
                else:
                    print(u'重试3次失败，结束程序')
                    exit(1)

    # 断开连接
    def close(self):
        self.chan.close()
        self.t.close()

    def exec_cmd(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("128.5.6.21", 22, "lingtj", "lingtj123")
        # client.connect('ssh.example.com')
        stdin, stdout, stderr = client.exec_command('ls -l')
        print(stdout.readlines())
        client.close()

    # 发送要执行的命令
    def send(self, cmd):
        cmd += '\r'
        # 通过命令执行提示符来判断命令是否执行完成
        p = re.compile(r':~ #')

        result = ''
        # 发送要执行的命令
        self.chan.send(cmd)
        # 回显很长的命令可能执行较久，通过循环分批次取回回显
        while True:
            sleep(0.5)
            ret = self.chan.recv(65535)
            if len(ret)==0:
                print("结束")
                break
            ret = ret.decode('utf-8')
            result += ret
            if p.search(ret):
                print(result)
                return result

class DirFileHelper:
    def checkTargetFileOrCreate(self,targetpath,filename):
        '''
        判断指定路径下是否存在指定文件
        :param targetpath:指定路径
        :param filename:目标文件
        :return:返回BaseResultInfo类型的结果
        '''
        result= models.BaseResultInfo(0,"已初始化","")
        # 判断本地路径下是否已经存在指定文件
        fullname = os.path.join(targetpath, filename)
        if os.path.isfile(fullname):
            result.code=1
            result.result="existed"
        else:
            # 不保存在指定文件则创建
            # 先判断指定路径是否存在
            if os.path.exists(targetpath):
                pass
            else:
                # 不存在则创建
                os.makedirs(targetpath)
                # pass
             # 存在目录则创建文件
            try:
                file = open(fullname, 'w')
                result.code=6
                result.result="ok"
                result.message=fullname
                # os.mknod(fullname)
                # return fullname
            except Exception as e:
                print(e)
                result.code=-1
                result.result="error"
                result.message=e
                # return None
        return result


class FtpClient:
    def __init__(self,host,username,pwd,port=21):
        '''
        构造函数 需要url，name，pwd，以及端口

        :param host:
        :param username:
        :param pwd:
        :param port:
        '''
        self.host=host
        self.username=username
        self.pwd=pwd
        self.port=port
        self.url="%s:%s"%(self.host,self.port)

    def __ftpconnect(self):
        ftp=FTP()
        # 设置调试等级1
        '''
        1: print commands and responses but not body text etc.
        打印命令和响应，而不是正文文本。
        '''
        ftp.set_debuglevel(1)
        ftp.connect(self.host,self.port)
        ftp.login(self.username,self.pwd)
        # ftp.sendcmd()
        print(self.__testcontect())
        return ftp

    def __testcontect(self):
        '''
        测试是否已连接
        打印getwelcome
        :return:
        '''
        return(self.ftp.getwelcome())

    def download(self,targetpath,filename,remotepath=None):
        '''
        公开的下载方法
        :param targetpath:
        :param filename:要保存的文件名称
        :param remotepath:ftp中的路径
        :return:若下载成功则返回本地保存文件的全路径；否则返回None
        '''
        # 1 ftp连接
        ftp=self.__ftpconnect()
        # 2 判断指定路径下是否存在指定文件
        isExist= self.__checkExistFile(ftp,filename,remotepath)
        if isExist:
            # 下载
            fullname = self.__downloadfile(ftp, self.url, targetpath, filename)
            return fullname
        return None

    def __checkExistFile(self,ftp,filename,remotepath=None):
        '''
        判断指定url下是否存在指定文件，存在返回true，不存在返回false
        :param ftp:ftp对象
        :param filename:文件名称
        :param remotepath:ftp中的路径
        :return:
        '''
        if remotepath is not None:
            # 进入指定路径
            ftp.sendcmd(remotepath)
        # 判断是否存在指定文件
            cmd="ls %s"%filename
            response= ftp.sendcmd(cmd)
            # 需要在实际中查看响应是什么
            # ——————————————————————
            if response is not None:
                return True
        return False

    def __downloadfile(self,ftp,url,targetpath,filename):
        '''
        从指定url下载名为filename的文件下载到本地targetpath路径下
        :param ftp:ftp实例对象
        :param url:ftp下载地址
        :param targetpath:本地路径
        :param filename:下载文件名
        :return:将本地存储的文件全路径返回
        '''
        bufsize=1024
        # 以二进制的方式打开并可写
        dirHelper= DirFileHelper()
        result=dirHelper.checkTargetFileOrCreate(targetpath,filename)
        if result is not None:
            try:
                fileInfo=open(result,'wb')
                ftp.retrbinary('RETR %S'%url,fileInfo.write,bufsize)
                fileInfo.close()
                ftp.quit()
                return result
            #ftp的错误在ftplib中，ftplib.FTP中没有错误
            except ftplib.error_perm:
                print("error:ftp error user:%s,pwd:%s"%(self.username,self.pwd))
                ftp.quit()
                return

class SFtpClient:
    '''
    由于均使用paramiko包
    sftp与ParamikoClient保持一致
    '''
    def __init__(self ,ip, username, password,port=22, timeout=30):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout

        self.client = None
        self.channel = None
        # 链接失败的重试次数
        self.try_times = 3
        self.trans=None

    def __connect(self):
        if self.trans is None:
            self.trans=paramiko.Transport((self.ip, self.port))
            self.trans.connect(username=self.username, password=self.password)

    def __sftpconnect(self):
        pass

    def __checkExistFile(self,ftp,filename,remotepath=None):
        '''
        判断指定url下是否存在指定文件，存在返回true，不存在返回false
        :param ftp:ftp对象
        :param filename:文件名称
        :param remotepath:ftp中的路径
        :return:
        '''
        if remotepath is not None:
            # 进入指定路径
            ftp.sendcmd(remotepath)
        # 判断是否存在指定文件
            cmd="ls %s"%filename
            response= ftp.sendcmd(cmd)
            # 需要在实际中查看响应是什么
            # ——————————————————————
            if response is not None:
                return True
        return False

    def sftp_download(self, local, remote,filename):
        '''
        通过sftp的方式下载
        :param local:本地路径
        :param remote:远程路径
        :param filename:文件名
        :return:返回BaseResultInfo类型的结果
        '''
        if self.trans is None:
            self.__connect()
        if self.trans is not None:
            try:
                sftp=paramiko.SFTPClient.from_transport(self.trans)
                localfilefullpath=os.path.join(local,filename)
                remotefilefullpath=os.path.join(remote,filename)
                # 判断远端是否存在指定文件
                # 判断本地是否已经创建指定文件
                dirHelper = DirFileHelper()
                result = dirHelper.checkTargetFileOrCreate(local, filename)
                #不管本地是否存在均下载
                result_return = models.ReturnResultInfo(result.code, result.result, result.message)
                # 可能会出现重复文件会出错的问题，待测试
                sftp.get(remotefilefullpath,localfilefullpath)

                result_return.code=6
                result_return.result="ok"
                result_return.title="状态信息"
            # try:
            #     if os.path.isdir(local):  # 判断本地参数是目录还是文件
            #         for f in sftp.listdir(remote):  # 遍历远程目录
            #             sftp.get(os.path.join(remote + f), os.path.join(local + f))  # 下载目录中文件
            #     else:
            #         sftp.get(remote, local)  # 下载文件
            except IOError as ioerr:
                print("io error %s"%ioerr)
                result_return.title="内部错误"
                result_return.result="ioerror"
                result_return.message=ioerr.strerror
                result_return.code = -1
            except Exception as e:
                print('download exception:', e)
                result_return.title = "内部错误"
                result_return.result = "ioerror"
                result_return.message = e
                result_return.code=-1
            self.trans.close()
        return result_return

class ParamikoConn(object):
    def __init__(self,host,port,user,pwd):
        self.host=host
        self.port=port
        self.user=user
        self.pwd=pwd
        self.ssh=None

    def ssh_connect(self):
        try:
            self.ssh=paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(self.host,self.port,self.user,self.pwd)
        except Exception as e:
            print('ssh %s%s:%s'%(self.host,self.user,e))
            exit()

    def ssh_exec_cmd(self,cmd):
        stdin, stdout, stderr =self.ssh.exec_command(cmd)

        err_list=stderr.readlines()
        if len(err_list)>0:
            print('error:%s'%err_list[0])
            exit()
        else:
            print(stdout.read().decode())

    def ssh_close(self):
        self.ssh.close()

