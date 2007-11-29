# -*- coding: utf-8 -*-

from fileman.models import *
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django import newforms as forms
from django.contrib.auth.models import User
import os
from django import newforms as forms
from fileman.settings import *
import pickle, re
import operator
from django.contrib.auth.decorators import permission_required

class File:
    def __init__(self, name = None, path = None, isdir = None, size = None):
        self.name = name
        self.path = path
        self.isdir = isdir
        self.size = size
    def __cmp__(self, other):
        return cmp(self.name, other.name)

@login_required
def list(request, path = None):
    try:
        request.user.user_permissions.get(codename = "can_fm_list")
    except:
        return HttpResponseRedirect('/login/?next=%s' % request.path)
    if request.user.fileman_Setting.home is None or request.user.fileman_Setting.root is None:
        return render_to_response('error.html',
               {"msg": ["Не назначена корневая или домашняя директории"]},
                context_instance=RequestContext(request))
    if path is None:
        path = request.user.fileman_Setting.home
    if not os.path.exists(path):
        return render_to_response('error.html',
               {"msg": ["Несуществующий путь"]},
                context_instance=RequestContext(request))
    if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
        return render_to_response('error.html',
               {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
                 
    dirlist = []
    filelist = []
    for f in os.listdir(path):
        file = File(f, os.path.join(path, f))
        if os.path.isdir(os.path.join(path, f)):
            file.isdir = 1
            file.size = "Dir"
            dirlist.append(file)
        else:
            file.isdir = 0
            file.size = os.path.getsize(os.path.join(path, f))
            filelist.append(file)
        dirlist.sort()
        filelist.sort()
            
    buffer = listBuffer(request)
    for item in buffer:
        item.append(os.path.basename(item[0]))
    return render_to_response('list.html',
           {"pwd": path,
            "dirlist": dirlist,
            "filelist": filelist,
            "buffer": buffer,
            },
            context_instance=RequestContext(request))
list = permission_required('fileman.can_fm_list')(list)
            
class UploadForm:
    def __init__(self, data):
        self.errors = []
        if data.has_key('path'):
            self.path = data['path']
        else:
            self.path = None
        self.files = []
        i = 1;
        while 1:
            if not data.has_key('ufile%d' % i):
                break
            self.files.append(data['ufile%d' % i])
            i+=1
        
    def is_valid(self):
        if self.path is None:
            errors.append("Не указан путь")
        if len(self.files) == 0:
            errors.append("Нет файлов")
        if len(self.errors) > 0:
            return False
        else:
            return True
        
    def save(self):
        for file in self.files:
            f = open(os.path.join(self.path, file['filename']), 'w')
            f.write(file['content'])
            f.close()
        return True
        
@login_required
def upload(request):
    if request.POST:
        post_data = request.POST.copy()
        if re.search("^%s" % request.user.fileman_Setting.root, post_data['path']) is None:
            return render_to_response('error.html',
                   {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
        post_data.update(request.FILES)
        form = UploadForm(post_data)
        print 1
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/fm/list/%s' % form.path)
        else:
            return render_to_response('error.html',
               {"msg": form.errors},
                context_instance=RequestContext(request))
    else:
        return render_to_response('error.html',
               {"msg": ["Пустая форма"]},
                context_instance=RequestContext(request))
upload = permission_required('fileman.can_fm_add')(upload)
    
@login_required
def preview(request, path = None):
    if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
        return render_to_response('error.html',
               {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
    from PIL import Image
    size = 176, 176
    im = Image.open(path)
    im.thumbnail(size, Image.ANTIALIAS)
    response = HttpResponse(mimetype="image/png")
    im.save(response, "PNG")
    return response
    
@login_required
def getUrl(request, path):
    if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
        return render_to_response('error.html',
               {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
    for alias in Alias.objects.all():
        if path.startswith(alias.path):
            return HttpResponse(path.replace(alias.path, alias.url))
    return HttpResponse("Нет доступа из вне")
    
@login_required
def delete(request):
    if request.POST:
        if request.GET.has_key('next'):
            path = request.GET['next']
        else:
            path = ''
        for key in request.POST.keys():
            if re.search("^%s" % request.user.fileman_Setting.root, request.POST[key]) is None:
                return render_to_response('error.html',
                       {"msg": ["Нет доступа"]},
                         context_instance=RequestContext(request))
            try:
                os.rename(request.POST[key], os.path.join(BASKET_FOLDER, os.path.split(request.POST[key])[1]))
            except Exception, msg:
                if request.GET.has_key('xhr'):
                    return HttpResponse(msg)
                return render_to_response('error.html',
                       {"msg": msg},
                        context_instance=RequestContext(request))
        if request.GET.has_key('xhr'):
            return HttpResponse("success")
        return HttpResponseRedirect('/fm/list/%s' % path)
    else:
        return render_to_response('error.html',
               {"msg": ["Пустая форма"]},
                context_instance=RequestContext(request))
delete = permission_required('fileman.can_fm_del')(delete)
                
@login_required
def destraction(request):
    if request.POST:
        if request.GET.has_key('next'):
            path = request.GET['next']
        else:
            path = ''
        for key in request.POST.keys():
            if re.search("^%s" % request.user.fileman_Setting.root, request.POST[key]) is None:
                return render_to_response('error.html',
                       {"msg": ["Нет доступа"]},
                         context_instance=RequestContext(request))
            if os.path.isdir(request.POST[key]):
                try:
                    rmdir(request.POST[key])
                except Exception, msg:
                    if request.GET.has_key('xhr'):
                        return HttpResponse(msg)
                    return render_to_response('error.html',
                           {"msg": msg},
                            context_instance=RequestContext(request))
            else:
                try:
                    os.remove(request.POST[key])
                except Exception, msg:
                    if request.GET.has_key('xhr'):
                        return HttpResponse(msg)
                    return render_to_response('error.html',
                           {"msg": msg},
                            context_instance=RequestContext(request))
        if request.GET.has_key('xhr'):
            return HttpResponse("success")
        return HttpResponseRedirect('/fm/list/%s' % path)
    else:
        return render_to_response('error.html',
               {"msg": ["Пустая форма"]},
                context_instance=RequestContext(request))
destraction = permission_required('fileman.can_fm_destruct')(destraction)
                
@login_required
def rmdir(path):
    if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
        return render_to_response('error.html',
               {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
    for f in os.listdir(path):
        if os.path.isdir(os.path.join(path, f)):
            rmdir(os.path.join(path, f))
        else:
            os.remove(os.path.join(path, f))
    os.rmdir(path)
rmdir = permission_required('fileman.can_fm_del')(rmdir)
                
def move(request):
    pass

@login_required
def rename(request):
    if request.POST:
        if request.GET.has_key('next'):
            path = request.GET['next']
        else:
            path = ''
        for key in request.POST.keys():
            if re.search("^%s" % request.user.fileman_Setting.root, request.POST[key]) is None:
                return render_to_response('error.html',
                       {"msg": ["Нет доступа"]},
                         context_instance=RequestContext(request))
            os.rename(request.POST[key])
        return HttpResponseRedirect('/fm/list/%s' % path)
    else:
        return render_to_response('error.html',
               {"msg": ["Пустая форма"]},
                context_instance=RequestContext(request))
rename = permission_required('fileman.can_fm_rename')(rename)
                
@login_required
def createDir(request, path):
    os.mkdir(path)
    return HttpResponseRedirect('/fm/list/%s' % path)
createDir = permission_required('fileman.can_fm_add')(createDir)

@login_required
def addBuffer(request):
    if request.POST:
        path = request.POST['path']
        if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
            return render_to_response('fileman/error.html',
                   {"msg": ["Нет доступа"]},
                     context_instance=RequestContext(request))
        if request.POST['action'] == "copy":
            action = 1
        elif request.POST['action'] == "cut":
            action = 2
        buffer =  listBuffer(request)
        if not [path, 1] in buffer and not [path, 2] in buffer:
            buffer.append([path, action])
        #request.user.fileman_Setting.buffer = pickle.dumps(buffer)
        #request.user.fileman_Setting.save()
        request.user.fileman_Setting.writeBuffer(pickle.dumps(buffer))
        if request.GET.has_key('xhr'):
            return HttpResponse("success")
    else:
        return render_to_response('error.html',
               {"msg": ["Пустая форма"]},
                context_instance=RequestContext(request))
                
@login_required
def listBuffer(request):
    if request.user.fileman_Setting.buffer != "":
        buffer = pickle.loads(request.user.fileman_Setting.buffer.encode("utf8"))
    else:
        buffer = []
    return buffer

def removeBuffer(request):
    pass
    
@login_required
def clearBuffer(request):
    request.user.fileman_Setting.writeBuffer("")
    
@login_required
def past(request, path):
    if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
        return render_to_response('error.html',
               {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
    import shutil
    buffer = listBuffer(request)
    for item in buffer:
        to = os.path.basename(item[0])
        if os.path.exists(os.path.join(path, to)):
            to = os.path.splitext(to)[0]+"_1"+os.path.splitext(to)[1]
        i=2
        while os.path.exists(os.path.join(path, to)):
            to = os.path.splitext(to)[0][:-1]+str(i)+os.path.splitext(to)[1]
            i+=1
        if item[1] == 1:
            shutil.copy(item[0], os.path.join(path, to))
        elif item[1] == 2:
            shutil.move(item[0], os.path.join(path, to))
            pass
    clearBuffer(request)
    return HttpResponseRedirect('/fm/list/%s' % path)
past = permission_required('fileman.can_fm_rename')(past)

@login_required
def RemoveFromBuffer(request, path):
    if re.search("^%s" % request.user.fileman_Setting.root, path) is None:
        return render_to_response('error.html',
               {"msg": ["Нет доступа"]},
                 context_instance=RequestContext(request))
    buffer =  listBuffer(request)
    if [path, 1] in buffer:
        buffer.remove([path, 1])
    elif [path, 2] in buffer:
        buffer.remove([path, 2])
    request.user.fileman_Setting.writeBuffer(pickle.dumps(buffer))
    return HttpResponse("success")
    
@login_required
def listBasket(request):
    return list(request, BASKET_FOLDER)
listBasket = permission_required('fileman.can_fm_del')(listBasket)