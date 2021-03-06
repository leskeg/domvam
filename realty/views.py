# -*- coding: utf-8 -*-
from django.shortcuts import render, render_to_response, redirect
# from django.http import HttpResponseRedirect
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, QueryDict, HttpResponseNotModified
from django_ajax.decorators import ajax
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from helpers import *
from django.views.decorators.csrf import csrf_exempt
# from myregions import my_regions
import json
from pprint import pprint
import os, os.path

from models import ProfileAgency, Region, Advert, Advert_Users, Currency, HEATING_CHOICES, ELECTRICITY_CHOICES, SEWERAGE_CHOICES, Profile, Ticket, Myregions, Cities, Streets
from forms import AgencyForm, Filter, AddCard, RegisterForm, AddCardRentFlat, AddCardRentRoom, AddCardRentHouse,AddCardRentArea, AddCardSaleFlat,AddCardSaleHouse, AddCardSaleArea, TicketForm, AddCardCommercial
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect
from django.template.context import RequestContext
from franchising.settings import REGION_TR, MEDIA_ROOT, CAT_TABS_COMMERCIAL, CAT_TYPE_COMMERCIAL, MY_REGIONS

# Create your views here.
from mongoengine.django.auth import User
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages

from django.utils.datastructures import MultiValueDict
import re
from django.http import Http404
from random import randint
import shutil
import pprint
from itertools import chain
from operator import attrgetter
from hashlib import md5
from PIL import Image, ImageFile
# from validate_email import validate_email
@csrf_exempt
def add_agency_details(request):
    if request.method == 'POST':
        new_info = request.POST.copy()
        del new_info['csrfmiddlewaretoken']
        obj_id = new_info['agency_id']
        this_profile = ProfileAgency.objects.get(id=obj_id)
        del new_info['agency_id']
        
        this_profile.description = new_info['description']
        this_profile.worktime = new_info['worktime']
        this_profile.domain = new_info['domain']

        this_profile.save()

        return redirect('/agency-page'+obj_id)

    else:
        obj_id = request.GET["obj_id"]

        return render(request, 'add_agency_details.html',{
            'obj_id': obj_id
            })

def agency_list(request):
    agencies = ProfileAgency.objects.all()
    return render(request, 'agency_list.html',{
        'agencies': agencies,
        'agency_count': agencies.count()
        })


def custom_404(request):
    return render_to_response('404.html')

def test(request):
    get_params = request.GET.copy()

    if "NAME" in get_params:
        SOATO = Cities.objects.filter(RAION=get_params["RAION"],OBL=get_params["OBL"].upper(),NAME=get_params["NAME"])[0]["SOATO"]
        # return Streets.objects.filter(SOATO=SOATO)
        return HttpResponse(Streets.objects.filter(SOATO=SOATO).to_json(), content_type="application/json")

    elif "RAION" in get_params:
        # return Cities.objects.filter(RAION=get_params["RAION"], OBL=get_params["OBL"].upper())
        return HttpResponse(Cities.objects.filter(RAION=get_params["RAION"], OBL=get_params["OBL"].upper()).to_json(), content_type="application/json")

    elif "OBL" in get_params:
        # return Cities.objects.filter(OBL=get_params["OBL"].upper())
        return HttpResponse(Cities.objects.filter(OBL=get_params["OBL"].upper()).to_json(), content_type="application/json")
    return

def ticket(request):
    if request.method == 'POST':
        request = request.POST.copy()
        ticket = TicketForm(request)
        if ticket.is_valid():
            Ticket(**ticket.cleaned_data).save()
            return redirect('/')
    else:
        ticket = TicketForm()
    return render(request,'ticket.html',{'ticket':ticket})

def my_cards(request):
    if request.user.is_authenticated():
        try:
            user =  Profile.objects.get(username=request.user.username)
        except:
            try:
                user =  ProfileAgency.objects.get(username=request.user.username)
            except:
                user = create_user_profile(request.user)

        my_ads = get_my_cards(user)
    else:
        my_ads = None

    return render(request, "my_cards.html", 
        {
            'ads': my_ads,
        }
    )

def favorite_cards(request):
    if request.user.is_authenticated():
        try:
            user =  Profile.objects.get(username=request.user.username)
        except:
            try:
                user =  ProfileAgency.objects.get(username=request.user.username)
            except:
                user = create_user_profile(request.user)

        my_ads = get_my_favorites(user)
    else:
        my_ads = None

    filter_obj = Filter({"group":"living", "cat_tab":"flat"})
    try:
        favorites = user.favorites
    except:
        favorites = []
    return render(request, "favorite_cards.html", 
        {
            'ads': my_ads,
            'filter_obj': filter_obj,
            "myfav": favorites,
            "mode": "favorites", 
        }
    )

@csrf_exempt
def action_card(request):
    if request.method == 'POST':
        is_agency = False
        if '_delete' in request.POST:
            try:
                ad = Advert_Users.objects(id=request.POST["_delete"]).get()
            except:
                ad = Advert.objects(id=request.POST["_delete"]).get()

            try:
                shutil.rmtree(os.path.join(settings.MEDIA_ROOT, request.POST["_delete"]))
            except:
                pprint.pprint(request.POST["_delete"] +'images forlder does not exist')

            try:
                Advert_Users.objects(id=request.POST["_delete"]).delete()
            except:
                Advert.objects(id=request.POST["_delete"]).delete()

        elif '_extend' in request.POST:
            try:
                ad = Advert.objects(id=request.POST["_extend"]).get()
            except:
                ad = Advert_Users.objects(id=request.POST["_extend"]).get()

            ad.adding_date = datetime.now()
            ad.expiring_date = ad.adding_date + timedelta(days=30)
            ad.save()

        elif '_edit' in request.POST:
            try:
                ad = Advert_Users.objects(id=request.POST["_edit"]).get()
            except:
                ad = Advert.objects(id=request.POST["_edit"]).get()
            
            if not ad["region"].startswith(u"г. "):
                ad["region"] = ad["region"].title()

            if not u" Область" in ad["region"] and not ad["region"].startswith(u"г. "):
                ad["region"] = u"г. " + ad["region"]

            mydict = json.loads(ad.to_json())

            options=[
                u'action_type',
                u'group',
                u'cat_tab',
                u'cat_type',
                u'region',
                u'region2',
                u'currency',
                u'number_of_rooms',
                u'balcony_deck',
                u'wall_material',
                u'wc',
                u'flooring',
                u'repair',
                u'type_of_house',
                u'period'
            ]

            for option in options:
                try:
                    mydict[ option + '_0'] = mydict.pop(option)
                except:
                    pass

            try:
                mydict[u'region__0'] = mydict[u'region2_0']
                mydict[u'region2'] = mydict[u'region2_0']
            except:
                pass

            if mydict['group_0'] == 'commercial':
                del mydict['cat_tab_0']

            # mydict[u'agreement'] = False
            qdict = QueryDict('')
            qdict = qdict.copy()
            qdict.update(mydict)
            add_form = AddCard(mydict)

            try:
                user_profile = Profile.objects.get(username=request.user.username)
            except:
                user_profile = ProfileAgency.objects.get(username=request.user.username)
                is_agency = True
            
            return render(request, "add_card.html", 
                {
                    "ad": ad,
                    "form": add_form,
                    "editform": True,
                    "is_agency": is_agency,
                    'user_profile': user_profile,
                }
            )

        return redirect('/my-cards')

def user_profile(request):
    if request.user.is_authenticated():
        username = request.user.username
        user_reviews = Advert.objects(reviews__username=username)
        try :
            user_profile = Profile.objects.get(username=username)
            is_agency=False
        except:
            try:
                user_profile =  ProfileAgency.objects.get(username=request.user.username)
                is_agency=True
            except:
                user_profile = create_user_profile(request.user)
                is_agency=False

        my_reviews = {}
        for ad in user_reviews:
            my_reviews[ad] = []
            for review in ad.reviews:
                if review['username'] == username:
                    my_reviews[ad].append(review)

        filter_obj = Filter({"group":"living", "cat_tab":"flat"})       
        return render(request, "user_profile.html", 
            {
            'filter_obj': filter_obj, 
            'my_reviews': my_reviews,
            'user': user_profile,
            'is_agency': is_agency,
            'user_profile': True,
            }
        )
    else:
        return redirect('/')

def agency_page(request, obj_id):
    this_agency = ProfileAgency.objects.get(id=obj_id)
    ads = Advert_Users.objects.filter(username=this_agency.username)
    filter_obj = Filter({"group":"living", "cat_tab":"flat"})
    return render(request, "user_profile.html", 
            {
            'filter_obj': filter_obj, 
            'user': user_profile,
            'agency_page': True,
            'this_agency': this_agency,
            'ads':ads,
            }
        )

def feedback(request, obj_id, review_id):
    # TODO: reimplemetn with django forms!
    if request.method == 'POST' and request.POST['feedback']:
        ad = Advert.objects(id=obj_id).get()
        feedback = {
            "username": request.POST['username'], # Do not use ever dirty values from POST!
            "date": datetime.now(),
            "text": request.POST['feedback'], # same danger
        }

        try:
            feedback_bck = ad["reviews"][int(review_id)]["feedback"]
        except:
            feedback_bck = []

        feedback_bck.append(feedback)
        ad["reviews"][int(review_id)]["feedback"] = feedback_bck
        ad.save()    
    else:
        pass

    return HttpResponseRedirect('/card/' + obj_id )
    # return redirect('/')

def add_review(request, obj_id):
    if request.method == 'POST' and request.POST['review']: # same warnign. you definitely not should do like this
        ad = Advert.objects(id=obj_id).get()

        try:
            review_id = ad.number_of_reviews
        except:
            ad.number_of_reviews = 0
            ad.save()
            review_id = 0

        review = {
            "username": request.POST['username'],
            "date": datetime.now(),
            "text": request.POST['review'],
            "review_id": review_id
        }
        ad.update(push__reviews=review)
        ad.update(inc__number_of_reviews=1)

        # ad.objects.get_or_create(review=review)

    else:
        pass

    return HttpResponseRedirect('/card/' + obj_id )
    # return redirect('/')


# from django.core.mail import send_mail
@csrf_exempt
@require_http_methods(['POST'])
@ajax
def register(request):
    Registerform = RegisterForm(request.POST)
    Registerform.is_valid()

    username = Registerform.cleaned_data["username"]
    password = Registerform.cleaned_data["password"]
    email = Registerform.cleaned_data["email"]

    errorExists = False

    if User.objects.filter(username=username).count() > 0:
        errorExists = True
        answer = 'error: Пользователь уже существует'
    
    if User.objects.filter(email=email).count() > 0:
        errorExists = True
        answer = 'error: E-mail уже существует'

    if not errorExists:

        User.create_user(username,password,email)
        user = User.objects.get(username=username)

        Profile(**Registerform.cleaned_data).save()
        user = authenticate(username=username, password=password)
        os.system('echo "Click in following link to activate your account: http://domvam.by/enable_user/?id=' + str(user.id) + '"| mail -s "Domvam e-mail verification" ' + email)
        user.is_active = False
        user.save()

        return u'Мы посылаем письмо к вам, пожалуйста, проверьте свою электронную почту, чтобы активировать аккаунт'

    else:
        return answer

@csrf_exempt
@require_http_methods(['POST'])
@ajax
def registerAgency(request):
    Registerform = RegisterForm(request.POST)
    Registerform.is_valid()

    username = Registerform.cleaned_data["username"]
    password = Registerform.cleaned_data["password"]
    email = Registerform.cleaned_data["email"]

    errorExists = False

    if User.objects.filter(username=username).count() > 0:
        errorExists = True
        answer = 'error: Пользователь уже существует'
    
    if User.objects.filter(email=email).count() > 0:
        errorExists = True
        answer = 'error: E-mail уже существует'

    if ProfileAgency.objects.filter(name_of_entity=request.POST['name_of_entity']).count() > 0:
        errorExists = True
        answer = u'error: Это имя агентства ("' + request.POST['name_of_entity'] + u'") уже зарегистрирован'

    if ProfileAgency.objects.filter(username=username).count() > 0:
        errorExists = True
        answer = u'error: Это имя пользователя ("' + username + u'") уже существует'

    if not errorExists:
        try:
            Agencyform = AgencyForm(request.POST)
            Agencyform.is_valid()
            ProfileAgency(**Agencyform.cleaned_data).save()
            User.create_user(username,password,email)
            user = User.objects.get(username=username)
            user.is_active = False
            user.save()
            os.system('echo "Click in following link to validate your email: http://domvam.by/validate_email_agency/?id=' + str(user.id) + '"| mail -s "Domvam e-mail verification" ' + email)
            return u'Мы посылаем письмо к вам, пожалуйста, проверьте свою электронную почту, чтобы активировать аккаунт'
        except:
            answer = 'error: Error'

    else:
        return answer

def login_view(request):
    if request.method == 'POST':
        Registerform = RegisterForm(request.POST)
        Registerform.is_valid()
        username = Registerform.cleaned_data['username']
        try:
            user = User.objects.get(username=username)
        except:
            try:
                user = User.objects.get(email=username)
            except:
                user = None
        
        # user = authenticate(username=username, password=password)
        if user is not None:
            password = Registerform.cleaned_data['password']
            if user.check_password(password) and user.is_active: # Redirect to a success page.
                user.backend = 'mongoengine.django.auth.MongoEngineBackend'
                login(request, user)
                # request.session.set_expiry(60 * 60 * 1) # 1 hour timeout                 
                return redirect('/')
                # return HttpResponse('logged')
            else: # Return an 'invalid login' error message.
                pass
                # return HttpResponse('disabled account')
                # Return a 'disabled account' error message
        else: 
            messages.add_message(request, messages.INFO, "Неправильное имя пользователя или пароль")
            # return HttpResponse('invalid login')
            # messages.add_message(request,messages.ERROR,u"Incorrect login name or password !")
            # return render(request, 'login.html', {})
    else:
        Registerform = RegisterForm()

    return render(request, "login.html", 
        {
        'RegisterForm': Registerform,
        }
    )
 
def admin_login(request):
    if request.method == 'POST':
        Registerform = RegisterForm(request.POST)
        Registerform.is_valid()
        username = Registerform.cleaned_data['username']
        try:
            user = User.objects.get(username=username)
        except:
            try:
                user = User.objects.get(email=username)
            except:
                user = None
        
        # user = authenticate(username=username, password=password)
        if user is not None:
            password = Registerform.cleaned_data['password']
            if user.check_password(password) and user.is_active: # Redirect to a success page.
                user.backend = 'mongoengine.django.auth.MongoEngineBackend'
                login(request, user)
                # request.session.set_expiry(60 * 60 * 1) # 1 hour timeout
                if user.is_superuser and user.is_staff and user.is_active:
                    return redirect('/adminpage')
                else:
                    return redirect('/')
                # return HttpResponse('logged')
            else: # Return an 'invalid login' error message.
                pass
                # return HttpResponse('disabled account')
                # Return a 'disabled account' error message
        else: 
            messages.add_message(request, messages.INFO, "Неправильное имя пользователя или пароль")
            # return HttpResponse('invalid login')
            # messages.add_message(request,messages.ERROR,u"Incorrect login name or password !")
            # return render(request, 'login.html', {})
    else:
        Registerform = RegisterForm()

    return render(request, "admin_login.html", 
        {
        'RegisterForm': Registerform,
        }
    )

    # data = {
    #     'RegisterForm': Registerform,
    # }
    # return render_to_response('login.html', data, context_instance=RequestContext(request))

def logout_view(request):
    logout(request)
    return redirect('/')
    # return HttpResponse('bye')

def _static(request):
    pass

def home(request, **kwargs):
    # request.GET - original, from browser GET 
    # get_params - GET with default values
    get_params = request.GET.copy()
    get_params_len = len(get_params)
    # import pprint
    # pprint.pprint(get_params)

    # if "form-side" in get_params.keys():
    #     mydict.keys()[mydict.values().index(16)]
    #     get_params['cat_tab'] = settings.REALT_CAT_TR[ get_params['cat_tab'] ]
    #     get_params['action_type']  = settings.REALT_ACTION_DICT[ get_params['action_type'] ]

    if not "group" in get_params.keys():
        get_params['group'] = "living"

    if "group" in get_params.keys() and not "cat_tab" in get_params.keys():
        if get_params['group'] == "living":
            get_params['cat_tab'] = "flat"
        elif get_params['group'] == "commercial":
            get_params['cat_tab'] = "building"


    get_params.update({
        # "sort_order": "-adding_date",
        "sort_order": "-adding_date",
        "currency": "usd",
        "view_type": "big", # big\small\map
        "convert_currency_to": "usd",
        "action_type": "sale",
    })
    get_params.update(request.GET.copy()) # f**ing django forms!!!


    filter_obj = Filter(get_params)
    filter_obj.is_valid() # call here to use cleaned_data

    # regions = Region.objects.dict_all()

    # default params:
    # query_params = {}
    query_params = {
        "price__exists":            True, 
    #     "number_of_rooms__exists":  True,
    #     "total_area__exists":       True,
    #     "living_area__exists":      True,
    #     "kitchen_area__exists":     True,
    #     "floor__exists":            True,
    #     "number_or_floors__exists": True,
        'images_len__gt':               1,
    }

    if filter_obj.is_valid():
        flag = False
        for k,v in filter_obj.cleaned_data.iteritems():
            if not v == "":
                flag = True
                break
        # TODO: we need to refactor filtering
        # There are no any filtering at mainpage
        if flag:
            # flag == True, shows, that Data exists

            # do not show "best" adverts if use start filtering
            if get_params_len > 0:
                query_params = {}

            if not filter_obj.cleaned_data['region'] == "":
                region_slug = Region.objects.filter(slug=filter_obj.cleaned_data['region']).get404()
                query_params['region'] = region_slug.name

            # simple queries 
            for key in ['group', 'cat_type', 'number_of_rooms', 'action_type']:
                if not filter_obj.cleaned_data[key] == "":
                    #more complicated queries
                    if key == 'number_of_rooms':
                        query_params[key+"__gte"] = str(filter_obj.cleaned_data[key])

            # assume that cat_tab exists each call
            if 'cat_type' not in get_params.keys() or get_params['cat_type'].strip() == '':
                if 'cat_type' in query_params.keys():
                    del query_params['cat_type']

                query_params['cat_type__in'] = zip(*filter_obj.fields['cat_type'].choices)[0]

            
            for mystring in ['price', 'living_area', 'kitchen_area', 'total_area', 'floors']:
                query_lte_gte(filter_obj,mystring,query_params)

            for mystring in ['heating', 'sewerage', 'electricity']:
                query_inside(filter_obj, mystring, query_params)

            if filter_obj.cleaned_data['garage'] == 'yes':
                query_params['garage__exists'] = True

            if filter_obj.cleaned_data['water'] == 'yes':
                query_params['water__exists'] = True

            if filter_obj.cleaned_data['with_photo'] == True:
                query_params['images_len__gt'] = 0

            query_params[ 'action_type__in' ] = re.sub("[^\w]", " ",  filter_obj.cleaned_data['action_type']).split()
            # query_params[ 'adding_date__gte' ] = datetime.now() - timedelta(days=30)
        else:
            # No Data exists
            pass

    modify_text = False
    new_title = False
    # new_description = False
    if 'filter_words' in kwargs:
        modify_text = True
        url_filtering = kwargs['filter_words'].split('-')

        for index, word in enumerate(url_filtering):
            if word == 'living' or word == 'commercial':
                query_params['group'] = word
                continue

            if word == 'liv_misc':
                query_params['group'] = 'living'
                # del query_params['cat_type']
                new_title = word
                continue

            if word == 'flat' or word == 'house' or word == 'area':
                query_params['group'] = 'living'
                if word == 'flat':
                    query_params['cat_type__in'] = [word]
                else:
                    query_params['cat_tab'] = word
                
                new_title = word
                continue

            if word == 'building' or word == 'premise' or word == 'land' or word == 'business':
                query_params['group'] = 'commercial'
                query_params['cat_tab'] = word

                new_title = word
                continue

            if word == 'sale' or word == 'rent':
                query_params['action_type__contains'] = word
                # query_params["__raw__"] = {'action_type': {'$regex': word}}
                continue
            elif word == 'exchange':
                query_params['action_type'] = 'sale'
                query_params['exchange'] = True
                continue

            if word == 'in':
                query_params['region'] = REGION_TR[url_filtering[index+1].title()]
                continue

    if 'group' in query_params and 'cat_tab' in query_params and query_params['group'] == 'commercial':
        change_tab_cat_type = query_params['cat_tab']
    else:
        change_tab_cat_type = None

    limit = datetime.now() - timedelta(days=30)
    # query_params["__raw__"] = {'adding_date': {'$gt': limit} }
    # query_params["__raw__"] = { '$or': [ {'adding_date': {'$gt': limit} }, {'expiring_date': {'$gt': datetime.now()} } ] }

    merge_ads_list = do_filtering(query_params, get_params['sort_order'])

    ads_count = merge_ads_list.count()

    paginator = Paginator(merge_ads_list, 12)
    page = request.GET.get('page')
    try:
        ads = paginator.page(page)
    except PageNotAnInteger:
        ads = paginator.page(1)
    except EmptyPage:
        ads = paginator.page(paginator.num_pages)

    # ads = list(ads[:25])
    # ads = Advert._get_db().command('text', 'advert', search=u"комната")
    # ads = ads['results']
    # ads = [x['obj'] for x in ads]
    # ads = []
    
    # ads_count = len(ads)


    # print filter_obj.cat_type


    # objects = Currency.objects.all()
    # out = {}
    # for obj in objects:
    #     out[obj['charcode'].lower()] = obj
    # out['byr'] = {'rate': 1, "scale": 1}

    _to_curr = 'byr'
    for ad in ads:
        ad.price = price_convert(float(ad.price), ad.currency, _to_curr)
        ad.currency = _to_curr

    if "icon_view" in get_params.keys():
        if get_params[ "icon_view" ] == "list-view":
            viewTemplate = "list"
        elif get_params[ "icon_view" ] == "grill-view":
            viewTemplate = "blocks"
    else:
        get_params['icon_view'] = "list-view"
        viewTemplate = "list"

    tab = "filter_" + get_params['cat_tab'] + ".html"

    query_params['current_status'] = 'vip-normal'
    try:
        user =  Profile.objects.get(username=request.user.username)
        myfav = user.favorites
        # myfav = [x.encode('ascii') for x in myfav]
    except:
        myfav = False

    try:
        ads_vip_normal = Advert.objects(**query_params)
        ads_vip_normal = ads_vip_normal[randint(1,len(ads_vip_normal))-1]
    except:
        ads_vip_normal = None

    query_params['current_status'] = 'vip-super'
    try:
        ads_vip_super = Advert.objects(**query_params)
        ads_vip_super = ads_vip_super[randint(1,len(ads_vip_super))-1]
    except:
        ads_vip_super = None
        
    cat_tabs_commercial = tuple(settings.CAT_TABS_COMMERCIAL)

    # countAdsRegion = {}
    # # query_params = {}
    # for region in settings.MY_REGIONS:
    #     query_params['region'] = region
    #     ads_regions = Advert.objects(**query_params)
    #     countAdsRegion[region] = ads_regions.count(False)
    #     ads_regions = Advert_Users.objects(**query_params)
    #     countAdsRegion[region] = countAdsRegion[region] + ads_regions.count(False)

    Agencyform = AgencyForm()

    return render(request, "main_page.html", 
        {
            # "regions": regions, 
            "filter_obj": filter_obj,
            "ads":ads, 
            "ads_count": ads_count,
            "get_params": get_params,
            "viewTemplate": viewTemplate,
            "tab": tab,
            "myfav": myfav,
            "ads_vip_super": ads_vip_normal,
            "ads_vip_normal": ads_vip_super,
            "cat_tabs_commercial": cat_tabs_commercial,
            # "countAdsRegion": countAdsRegion,
            'change_tab_cat_type': change_tab_cat_type,
            'Agencyform': Agencyform,
            "main_page": True,
            'modify_text': modify_text,
            'new_title': new_title,
            # 'ads_list': merge_ads_list[0:99],
        }
    )

def card(request, obj_id):
    try:
        ad = Advert.objects(id=obj_id).get()
    except:
        try:
            ad = Advert_Users.objects(id=obj_id).get()
        except:
            return render(request, "404.html")

    try:
        ad.update(inc__number_of_views=1)
    except:
        ad.update(push__number_of_views=1)

    query_params = {'images_len__gt': 1, 'cat_type': ad.cat_type }
    my_random = randint(0,1000)
    random_ads = Advert.objects(**query_params).order_by('-number_of_views')[my_random:my_random+3]

    # title generation!!
    h1_title = u''
    if "rent" in ad["action_type"]:
        if "period" in ad and "day" in ad.period:
            h1_title = tr_type_of_action("day")           
        else:
            h1_title = tr_type_of_action("rent")
    else:
        if "exchange" in ad or ad["action_type"] == "exchange":
            h1_title = tr_type_of_action("exchange")
        else:
            h1_title = tr_type_of_action("sale")

    if "number_of_rooms" in ad and ad["cat_type"] == "flat" or ad["cat_type"] == "new":
        h1_title = h1_title + ' ' + tr_number_of_rooms(ad["number_of_rooms"])
        if "exchange" in ad or ad["action_type"] == "exchange":
            h1_title = h1_title + u'ой'
        else:
            h1_title = h1_title + u'ую'

    if "cat_type" in ad and ad["group"] == "living":
        if ad["cat_type"] == "flat" or ad["cat_type"] == "room":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])
            if "exchange" in ad or ad["action_type"] == "exchange":
                h1_title = h1_title + u'ы'
            else:
                h1_title = h1_title + u'у'

        elif ad["cat_type"] == "new":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])
            if "exchange" in ad or ad["action_type"] == "exchange":
                h1_title = h1_title + u'ки'
            else:
                h1_title = h1_title + u'у'

        elif ad["cat_type"] == "house" or ad["cat_type"] == "cottage" or ad["cat_type"] == "garage":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])
            if "exchange" in ad or ad["action_type"] == "exchange":
                h1_title = h1_title + u'а'

        elif ad["cat_type"] == "dacha":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])
            if "exchange" in ad or ad["action_type"] == "exchange":
                h1_title = h1_title + u'и'
            else:
                h1_title = h1_title + u'у'

        elif ad["cat_type"] == "half_house":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])

        elif ad["cat_type"] == "area":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])
            if "exchange" in ad or ad["action_type"] == "exchange":
                h1_title = h1_title + u'а'
            else:
                h1_title = h1_title + u'ок'

        elif ad["cat_type"] == "parking_lot":
            h1_title = h1_title + ' ' + tr_cat_type2(ad["cat_type"])
            if "exchange" in ad or ad["action_type"] == "exchange":
                h1_title = h1_title + u'а'
            else:
                h1_title = h1_title + u'о'

    elif "cat_type" in ad and ad["group"] == "commercial":
        h1_title = h1_title + ' ' + translate_to_ru2(ad["cat_type"])

    h1_title = h1_title + ' ' + u'в'

    if "region3" in ad:
        h1_title = h1_title + ' ' + ad["region3"] + ' '
    if "region2" in ad:
        h1_title = h1_title + ' ' + ad["region2"] + ' '
    if "region" in ad:
        h1_title = h1_title + ' ' + ad["region"] + ' '

    h1_title = h1_title + ad["address"]
    if "house" in ad:
        h1_title = h1_title + ' ' + ad["house"]

    ad.h1_title = h1_title

    window_title = u''
    if h1_title.startswith(u"Сдам"):
        window_title = h1_title.replace(u"Сдам", u"Снять")
    elif h1_title.startswith(u"Продам"):
        window_title = h1_title.replace(u"Продам", u"Купить")
    elif h1_title.startswith(u"Обмен"):
        window_title = h1_title.replace(u"Обмен", u"Обмен")
    elif h1_title.startswith(u"Сдам на сутки"):
        window_title = h1_title.replace(u"Сдам на сутки", u"Снять на сутки")

    ad.action_type_bck = ad.action_type
    try:
        ad.action_type = settings.REALT_ACTION_DICT[ ad.action_type ]
    except:
        ad.action_type = settings.REALT_CAT_TR[ ad.group.encode() ]

    # information fields intersection 
    intersect = list(set(dir(ad)).intersection(settings.KEYS))
    info_fields = {}
    for field in intersect:
        if ad[field] is not None: 
            info_fields[field] = settings.DICT1[field]


    ad.other_prices = {}

    for cur in ["usd", "byr", "eur"]:
        if cur == ad.currency:
            ad.other_prices[cur] = ad.price
            continue

        ad.other_prices[cur] = price_convert(ad.price, ad.currency, cur)

    window_title = window_title + ' ' + str(int(ad.other_prices["byr"])) + " BYR"

    ad.window_title = window_title

    appliance_layout = {}

    for key in list(set(["city_phone", "furniture", "home_appliances", "internet"]).intersection(ad.__dict__.keys())):
        if key in info_fields.keys():
            appliance_layout[key] = info_fields[key]
            del info_fields[key]

    get_params = {}
    get_params['group'] = "living"
    get_params['cat_tab'] = "flat"
    filter_obj = Filter(get_params)
    filter_obj.is_valid()

    try:
        if request.user.username == ad.username:
            myadd = True
        else:
            myadd = False
    except:
            myadd = False

    try:
        user =  Profile.objects.get(username=request.user.username)
        if user.favorites.count(obj_id) == 1:
            myfav = True
        else:
            myfav = False
    except:
        myfav = False

    return render(request, "one_card.html", 
        {
            "ad": ad,
            "filter_obj": filter_obj,
            "info_fields": info_fields,
            "appliance_layout": appliance_layout,
            "myadd": myadd,
            "myfav": myfav,
            "mode": "one_card",
            "random_ads": random_ads,
            "main_page": False,
        }
    )

def add_card(request):
    # sent = False
    # if request.method == "POST":
    #     request = request.POST.copy()
    #     user_error = False

    #     if '_addCard' in request:
    #         sent = True

    #     if not request['username']:

    #         if request['usernameR']: # Register new user
    #             request['username'] = request['usernameR']
    #             request['email'] = request['emailR']
    #             request['password'] = request['passwordR']
    #             action = "Register"

    #         elif request['usernameL']: # Login user
    #             request['username'] = request['usernameL']
    #             request['email'] = request['emailL']
    #             request['password'] = request['passwordL']
    #             action = "Login"
    #         else:
    #             user_error = "You must login or register"

    #     Registerform = RegisterForm(request)
    #     if Registerform.is_valid():
    #         username = Registerform.cleaned_data["username"]
    #         password = Registerform.cleaned_data["password"]
    #         email = Registerform.cleaned_data["email"] 

    #         if action == "Register":
    #             try:
    #                 User.create_user(username,password,email)
    #                 user = authenticate(username=username, password=password)
    #                 login(request, user)
    #                 # if validate_email(email,verify=True):
    #                 #     User.create_user(username,password,email)
    #                 #     user = authenticate(username=username, password=password)
    #                 #     login(request, user)
    #                 # else:
    #                 #     user_error = "E-mail не существует"
    #             except:
    #                 user_error = "User already exists"

    #         elif action == "Login":
    #             try:
    #                 user = authenticate(username=username, password=password)
    #             except:
    #                 user = authenticate(username=email, password=password)

    #             try:
    #                 login(request, user)
    #             except:
    #                 user_error = "Incorrect login"
    #     else:
    #         user_error = "Incorrect user"

    #     add_form = AddCard(request, request.FILES)
    #     if add_form.is_valid():
    #     # if True:
    #         add_form.is_valid()

    #         if "sale" not in add_form.cleaned_data["action_type"]:
    #             add_form.cleaned_data["exchange"] = False

    #         if "rent" in add_form.cleaned_data["action_type"]:
    #             if "day" in request.POST.keys() and "month" in request.POST.keys():
    #                 add_form.cleaned_data["period"] = "day month"
    #                 del add_form.cleaned_data["day"]
    #                 del add_form.cleaned_data["month"]
    #             elif "month" in request.POST.keys():
    #                 add_form.cleaned_data["period"] = "month"
    #                 del add_form.cleaned_data["month"]
    #             elif "day" in request.POST.keys():
    #                 add_form.cleaned_data["period"] = "day"
    #                 del add_form.cleaned_data["day"]

    #         # action_type = re.sub("[^\w]", " ",  add_form.cleaned_data['action_type']).split() # Convert string in list
    #         # add_form.cleaned_data['action_type'] = action_type
    #         if "number_of_rooms" in request.POST.keys():
    #             add_form.cleaned_data["number_of_rooms"] = int(request.POST["number_of_rooms"])

    #         try:
    #             del add_form.cleaned_data['agreement']
    #             add_form.cleaned_data['title'] = REALT_ACTION_DICT[add_form.cleaned_data['action_type']]+' - '+REALT_CAT_TR[add_form.cleaned_data['cat_type']]+' - '+add_form.cleaned_data['number_of_rooms']+' - '+add_form.cleaned_data['region']+' - '+add_form.cleaned_data['street']

    #         except:
    #             try:
    #                 add_form.cleaned_data['title'] = add_form.cleaned_data['address']
    #             except:
    #                 pass

    #         if '_edit' in request.POST:
    #             obj_id = request.POST["ObjectId"]
    #             ad = Advert_Users.objects(id=obj_id).get()
    #             for key in add_form.cleaned_data:
    #                 if add_form.cleaned_data[key] == False:
    #                     myquery = "ad.update(unset__" + key + "=1)"
    #                 else:
    #                     myquery = "ad.update(set__" + key + "=" + "add_form.cleaned_data['" + key + "'])"
    #                 exec(myquery)

    #             return redirect('/card' + obj_id)

    #         else:

    #             for feature in ['furniture','home_appliances','internet']:
    #                 if not add_form.cleaned_data[feature]:
    #                     del add_form.cleaned_data[feature]

    #             for key in add_form.cleaned_data:
    #                 if add_form.cleaned_data[key] == False:
    #                     del add_form.cleaned_data[key]

    #             Advert(**add_form.cleaned_data).save()

    #             # doc_id = Advert()['doc_id']-1 # what is a purpose of using doc_id?
    #             ad = Advert.objects(**add_form.cleaned_data).get()
                
    #             original = []
    #             for f in request.FILES.getlist('FAKE_PATH'):
    #                 original.append( '/' + handle_add_images(f, ad.id) )

    #             images = {}
    #             images['original'] = original
    #             ad.images = images
    #             ad.images_len = len(request.FILES.getlist('FAKE_PATH'))
    #             ad.username = request['username']

    #             ad.expiring_date = ad.adding_date + timedelta(days=30)

    #             ad.save()
    #             return HttpResponseRedirect('/card' + str(ad.id) )
    #             # return redirect('/my-cards')

    # else:
    #     # mvd = MultiValueDict({u'FAKE_PATH': request.FILES.getlist('FAKE_PATH') })
    mydict = {u'group_0': "living" , u'cat_tab_0': u"flat", u'cat_type_0': u"flat", u"currency_0": u"usd"}
    qdict = QueryDict('')
    qdict = qdict.copy()
    qdict.update(mydict)
    add_form = AddCard(mydict)
    Registerform = RegisterForm()
    user_error = False
    sent = False

    try:
        user_profile = Profile.objects(username=request.user.username)[0]
        is_agency = False
    except:
        try:
            user_profile = ProfileAgency.objects(username=request.user.username)[0]
            is_agency = True
        except:
            user_profile = None
            is_agency = False

    Agencyform = AgencyForm()
    Registerform = RegisterForm()                

    return render(request, "add_card.html", 
        {
            "form": add_form,
            "RegisterForm": Registerform,
            "user_error": user_error,
            "sent": sent,
            'user_profile': user_profile,
            'is_agency': is_agency,
            'Agencyform': Agencyform,
        }
    )
    # add_form.changed_data
    # add_form.full_clean()
    # pprint.pprint(add_form.errors)
    # pprint.pprint(add_form['captcha'].errors)
    # if add_form.is_valid():
    # pprint.pprint(add_form.errors)

# Ajax section
@require_http_methods(["POST"])
@csrf_exempt
@ajax
def ajax_get_cat_tabs(request):
    form = AddCard(request.POST)
    form.full_clean()
    form.is_valid()
    # if form.is_valid() and form.has_changed() and "group" in form.changed_data:
    if form.has_changed() and "group" in form.changed_data:
        res = Advert.get_cat_tab_choices(form.cleaned_data['group'])
    else:
        res = []

    return res


#TODO: rewrite in more convient and flexible way!
@require_http_methods(["POST"])
@csrf_exempt
@ajax
def ajax_get_cat_types(request):
    form = AddCard(request.POST)
    form.is_valid()
    # if form.is_valid() and form.has_changed() and ("group" in form.changed_data and "cat_tab" in form.changed_data):

    if form.has_changed() and ("group" in form.changed_data and "cat_tab" in form.changed_data):
        res = Advert.get_cat_type_choices(
                    form.cleaned_data['group'], form.cleaned_data['cat_tab']
                )
    else:
        res = []

    return res

def my_filtering(get_params):
    if not 'group' in get_params.keys():
        get_params['group'] = "living"

    if 'group' in get_params.keys() and not 'cat_tab' in get_params.keys():
        if get_params['group'] == "living":
            get_params['cat_tab'] = "flat"
        elif get_params['group'] == "commercial":
            get_params['cat_tab'] = "building"
    
    query_params = {
        'price__exists': True,
    }

    query_params['group'] = get_params["group"]

    if get_params['group'] == "living":
        # @TODO: REwrite with django form Filter!!!!! 

        if get_params["cat_tab"] == "flat":
            if "cat_type" in get_params:
                query_params['cat_type__in'] = [get_params["cat_type"]]           

        elif get_params["cat_tab"] == "liv_misc":
            if 'cat_type' in get_params:
                query_params['cat_type'] = get_params["cat_type"]
            else:
                query_params['cat_type__in'] = ['garage', 'parking_lot', 'other_liv_misc']
        else:
            query_params['cat_type'] = get_params["cat_tab"]

        # if get_params['cat_tab'] != "liv_misc" and 'cat_type' in get_params:
        #     del get_params['cat_type']


        if 'number_of_rooms' in get_params and get_params["number_of_rooms"] != "":
            mylist = [int(x) for x in get_params["number_of_rooms"].replace(","," ").split()]
            if 5 in mylist:
                mylist.extend(range(6,10))
            query_params['number_of_rooms__in'] = mylist

    elif get_params["group"] == "commercial":
        query_params['cat_tab'] = get_params['cat_tab']
        if 'cat_type' in get_params:
            query_params['cat_type'] = get_params['cat_type']

    # query_params['action_type'] = get_params['action_type']
    if 'action_type' in get_params:
        query_params['action_type__icontains'] = get_params["action_type"]
        # query_params["__raw__"] = {
        #     "action_type": 
        #         {
        #             '$regex': get_params["action_type"] 
        #         }
        #     }

    if 'region' in get_params:
        query_params['region__icontains'] = get_params['region']

    if 'region2' in get_params:
        query_params['region2__icontains'] = get_params["region2"]

    # if 'period' in get_params:
    #     query_params['period__in'] = [get_params['period']]
    if 'period' in get_params:
        query_params['period__icontains'] = get_params["period"]
    # if 'period' in get_params:
    #     query_params["__raw__"] = {
    #         "period": 
    #             {
    #                 '$regex': get_params["period"] 
    #             }
    #         }
        
    if 'exchange' in get_params:
        query_params['exchange'] = True

    if 'title' in get_params and get_params["title"] != "":
        query_params['title__contains'] = get_params["title"]
        # query_params["__raw__"] = {
        #     "title": 
        #         {
        #             '$regex': get_params["title"] 
        #         }
        #     }

    if 'with_photo' in get_params and get_params['with_photo'] == "yes":
        query_params['images_len__gte'] = 1

    if not 'sort_order' in get_params:
        get_params["sort_order"] = "-adding_date"

    filter_obj = Filter(get_params)
    filter_obj.is_valid()
    for mystring in ['living_area', 'kitchen_area', 'total_area', 'plot_size_in_acros','floors']:
        query_lte_gte_(get_params,mystring,query_params)

    limit = datetime.now() - timedelta(days=30)
    # query_params["__raw__"] = { '$or': [ {'adding_date': {'$gt': limit} }, {'expiring_date': {'$gt': datetime.now()} } ] }


    # http://rate-exchange.appspot.com/currency?from=USD&to=EUR
    # {"to": "EUR", "rate": 0.85980000000000001, "from": "USD"}
    if ('price_min' in get_params or 'price_max' in get_params) and (get_params['price_min'] != '' or get_params['price_max'] != ''):
        if not 'currency' in get_params:
            get_params['currency'] = 'byr'

        query_params['currency'] = get_params['currency']
        query_lte_gte_(get_params,'price',query_params)

        merge_ads_list = do_filtering(query_params, get_params['sort_order'])

        if 'price_min' in get_params and get_params['price_min'] != '':
            price_min_original = get_params['price_min']
        if 'price_max' in get_params and get_params['price_max'] != '':
            price_max_original = get_params['price_max']

        currencies = ['usd','eur','byr']
        currencies.remove(get_params['currency'])
              
        for conversion in currencies:
            query_params['currency'] = conversion

            if 'price_min' in get_params and get_params['price_min'] != '':
                get_params['price_min'] = price_convert(float(price_min_original),get_params['currency'], conversion)
            if 'price_max' in get_params and get_params['price_max'] != '':
                get_params['price_max'] = price_convert(float(price_max_original),get_params['currency'], conversion)
            query_lte_gte_(get_params,'price',query_params)

            merge_ads_list2 = do_filtering(query_params, get_params['sort_order'])
            merge_ads_list = QuerySetChain(merge_ads_list,merge_ads_list2)

    else:
        merge_ads_list = do_filtering(query_params, get_params['sort_order'])
        
    ads_count = merge_ads_list.count()
    
    paginator = Paginator(merge_ads_list, 12)

    try:
        page = int(get_params['page'])
    except:
        page = 1

    try:
        ads = paginator.page(page)
    except PageNotAnInteger:
        ads = paginator.page(1)
    except EmptyPage:
        ads = paginator.page(paginator.num_pages)

    if not "convert_currency_to" in get_params:
        get_params['convert_currency_to']='byr'

    if "convert_currency_to" in get_params and not get_params['convert_currency_to'].strip() == "":
        _to_curr = get_params['convert_currency_to']

        for ad in ads:
            ad.price = price_convert(float(ad.price), ad.currency, _to_curr)
            ad.currency = _to_curr

    try:
        user =  Profile.objects.get(username=get_params['user'])
        myfav = user.favorites
    except:
        myfav = False


    query_params['current_status'] = 'vip-normal'

    try:
        ads_vip_normal = Advert.objects(**query_params)
        ads_vip_normal = ads_vip_normal[randint(1,len(ads_vip_normal))-1]
    except:
        ads_vip_normal = None

    query_params['current_status'] = 'vip-super'
    try:
        ads_vip_super = Advert.objects(**query_params)
        ads_vip_super = ads_vip_super[randint(1,len(ads_vip_super))-1]
    except:
        ads_vip_super = None
    
    my_obj = {
        # "ads_list": merge_ads_list[0:99],
        # "ads_list1": ads_list,
        # "ads_list2": ads_list2,
        "ads":ads, 
        "myfav": myfav,
        "ads_count": ads_count,
        "ads_vip_super": ads_vip_normal,
        "ads_vip_normal": ads_vip_super,
    }

    return my_obj

@require_http_methods(["GET"])
@ajax
def ajax_get_region_counters(request):
    get_params = request.GET.copy()
    countAdsRegion = {}
    for region in settings.MY_REGIONS:
        get_params['region'] = region
        countAdsRegion[region] = my_filtering(get_params)['ads_count']

    return countAdsRegion

@require_http_methods(["GET"])
@ajax
def ajax_get_filter(request):
    get_params = request.GET.copy()
    get_params['user'] = request.user.username
    my_obj = my_filtering(get_params)
    #return my_obj
    return render(request, "adverts.html", my_obj)

@require_http_methods(["GET"])
@ajax
def get_regions(request):

    return {
        "global_regions": Region.objects.all(),
        "regions": {
            'brest': "Брест",
            'gomel': "Гомель",
            'grodno': "Гродно",
            'minsk': "Минск",
            'mogilev': "Могилев",
            'vitebsk': "Витебск",
        }
    }

@require_http_methods(["GET"])
@ajax
def get_favorite_cards(request):
    if request.user.is_authenticated():
        try:
            user =  Profile.objects.get(username=request.user.username)
        except:
            try:
                user =  ProfileAgency.objects.get(username=request.user.username)
            except:
                user = create_user_profile(request.user)

        try:
            favorites = user.favorites
        except:
            favorites = []

    query_params = {}
    query_params[ 'id__in' ] = favorites
    
    if not "sort_order" in request.GET.keys():
        my_ads = do_filtering(query_params,"-adding_date")
    else:
        my_ads = do_filtering(query_params,request.GET['sort_order'])

    if "convert_currency_to" in request.GET.keys() and not request.GET['convert_currency_to'].strip() == "":
        _to_curr = request.GET['convert_currency_to']

    else:
        _to_curr = 'byr'

    for ad in my_ads:
        ad.price = price_convert(ad.price, ad.currency, _to_curr)
        ad.currency = _to_curr

    return render(request, "adverts.html", 
        {
            "ads":my_ads,
            "myfav":favorites, 
        }
    )

@require_http_methods(["GET"])
@ajax
def get_cards(request):
    if request.user.is_authenticated():
        try:
            user = Profile.objects.get(username=request.user.username)
        except:
            user = ProfileAgency.objects.get(username=request.user.username)

        try:
            favorites = user.favorites
        except:
            favorites = []

    if not "sort_order" in request.GET.keys():
        user_ads = list(Advert_Users.objects(username=user.username))
    else:
        user_ads = list(Advert_Users.objects(username=user.username).order_by(request.GET['sort_order']))

    my_ads = []
    for ad in user_ads:
        if ad['username'] == user.username:
            my_ads.append(ad)

    if "convert_currency_to" in request.GET.keys() and not request.GET['convert_currency_to'].strip() == "":
        _to_curr = request.GET['convert_currency_to']
        objects = Currency.objects.all()
        out = {}
        for obj in objects:
            out[obj['charcode'].lower()] = obj
        out['byr'] = {'rate': 1, "scale": 1}

        for ad in my_ads:
            ad.price = price_convert(ad.price, ad.currency, _to_curr)
            ad.currency = _to_curr

    return render(request, "adverts.html", 
        {
            "ads":my_ads,
            "myfav":favorites, 
        }
    )

@require_http_methods(["GET"])
@ajax
def add_favorite_card(request):
    if request.user.is_authenticated():
        try:
            user = Profile.objects.get(username=request.user.username)
        except:
            user = ProfileAgency.objects.get(username=request.user.username)

        try:
            if user.favorites.count(request.GET["obj_id"]) == 0:
                user.update(push__favorites=request.GET["obj_id"])
            else:
                user.update(pull__favorites=request.GET["obj_id"])
        except:
            user.update(push__favorites=request.GET["obj_id"])
    return

@require_http_methods(["GET"])
@ajax
def one_card(request):
    try:
        ad = Advert.objects(id=request.GET['id']).get()
    except:
        try:
            ad = Advert_Users.objects(id=request.GET['id']).get()
        except:
            return render(request, "404.html")

    try:
        ad.update(inc__number_of_views=1)
    except:
        ad.update(push__number_of_views=1)

    query_params = {'images_len__gt': 1, 'cat_type': ad.cat_type }
    my_random = randint(0,1000)
    random_ads = Advert.objects(**query_params).order_by('-number_of_views')[my_random:my_random+3]
    ad.action_type_bck = ad.action_type
    try:
        ad.action_type = settings.REALT_ACTION_DICT[ ad.action_type ]
    except:
        ad.action_type = settings.REALT_CAT_TR[ ad.group.encode() ]

    ad.cat_type = settings.REALT_CAT_TR[ ad.cat_type ]

    # information fields intersection 
    intersect = list(set(dir(ad)).intersection(settings.KEYS))
    info_fields = {}
    for field in intersect:
        if ad[field] is not None: 
            info_fields[field] = settings.DICT1[field]

    ad.other_prices = {}

    for cur in ["usd", "byr", "eur"]:
        if cur == ad.currency:
            ad.other_prices[cur] = ad.price
            # continue

        ad.other_prices[cur] = price_convert(ad.price, ad.currency, cur)

    appliance_layout = {}

    for key in list(set(["city_phone", "furniture", "home_appliances", "internet"]).intersection(ad.__dict__.keys())):
        if key in info_fields.keys():
            appliance_layout[key] = info_fields[key]
            del info_fields[key]

    get_params = {}
    get_params['group'] = "living"
    get_params['cat_tab'] = "flat"
    filter_obj = Filter(get_params)
    filter_obj.is_valid()

    try:
        if request.user.username == ad.username:
            myadd = True
        else:
            myadd = False
    except:
            myadd = False

    try:
        user =  Profile.objects.get(username=request.user.username)
        if user.favorites.count(request.GET['id']) == 1:
            myfav = [request.GET['id']]
        else:
            myfav = False
    except:
        myfav = False

    return render(request, "one_card.html", 
        {
            "ad": ad,
            # "filter_obj": filter_obj,
            "info_fields": info_fields,
            "appliance_layout": appliance_layout,
            "myadd": myadd,
            "myfav": myfav,
            "random_ads": random_ads,
        }
    )

@require_http_methods(["POST"])
@ajax
@csrf_exempt
def ajax_upload_image(request):
    handle_add_images(request.FILES['file'], request.POST['ObjectId'])
    
    path = os.path.join(settings.MEDIA_ROOT, str(request.POST['ObjectId']))
    savednames_original = os.listdir(path)

    original = []
    thumbs = []
    medium = []

    for filename in savednames_original:
        if not '-small' in filename and not '-medium' in filename:
            original.append( os.path.join(settings.STATIC_URL, settings.MEDIA_URL, str(request.POST['ObjectId']))+'/{0}'.format(filename) )

    for filename in savednames_original:
        if '-medium' in filename:
            medium.append( os.path.join(settings.STATIC_URL, settings.MEDIA_URL, str(request.POST['ObjectId']))+'/{0}'.format(filename) )

    for filename in savednames_original:
        if '-small' in filename:
            thumbs.append( os.path.join(settings.STATIC_URL, settings.MEDIA_URL, str(request.POST['ObjectId']))+'/{0}'.format(filename) )

    ad = Advert_Users.objects(id=request.POST['ObjectId']).get()
    images = {}
    images['original'] = original
    images['thumbs'] = thumbs
    images['medium'] = medium
    ad.images = images
    ad.images_len = len(original)
    ad.save()
    return

@require_http_methods(["POST"])
@ajax
@csrf_exempt
def ajax_add_card(request):
    if request.method == "POST" and request.user.is_authenticated():
        req = request.POST.copy()
        add_form = AddCard(req, request.FILES)
        add_form.is_valid()
        
        if "living" in add_form.cleaned_data["group"]:
            # Form selection according to action_type, cat_tab y cat_type
            if "sale" in add_form.cleaned_data["action_type"]:
                if "flat" in add_form.cleaned_data["cat_tab"]:
                    if "room" in add_form.cleaned_data["cat_type"]:
                        add_form = AddCardRentRoom(req, request.FILES)
                    else:
                        add_form = AddCardSaleFlat(req, request.FILES)
                elif "house" in add_form.cleaned_data["cat_tab"]:
                    add_form = AddCardSaleHouse(req, request.FILES)
                elif "area" in add_form.cleaned_data["cat_tab"]:
                    add_form = AddCardSaleArea(req, request.FILES)
                
            elif "rent" in add_form.cleaned_data["action_type"]:
                if "flat" in add_form.cleaned_data["cat_tab"]:
                    if "room" in add_form.cleaned_data["cat_type"]:
                        add_form = AddCardRentRoom(req, request.FILES)
                    else:
                        add_form = AddCardRentFlat(req, request.FILES)
                elif "house" in add_form.cleaned_data["cat_tab"]:
                    add_form = AddCardRentHouse(req, request.FILES)
                elif "area" in add_form.cleaned_data["cat_tab"]:
                    add_form = AddCardRentArea(req, request.FILES)

        elif "commercial" in add_form.cleaned_data["group"]:
            add_form = AddCardCommercial(req, request.FILES)

        if add_form.is_valid():
            add_form.is_valid()

            big_city = False
            for city in [u'г. Брест',u'г. Витебск',u'г. Гомель',u'г. Гродно',u'г. Минск',u'г. Могилев']:
                if city in add_form.cleaned_data["name"]:
                    big_city = True

            if big_city:
                add_form.cleaned_data["region"] = add_form.cleaned_data["name"]
                add_form.cleaned_data["region2"] = add_form.cleaned_data["raion"]
            else:
                add_form.cleaned_data["region"] = add_form.cleaned_data["obl"]
                add_form.cleaned_data["region2"] = add_form.cleaned_data["raion"]
                add_form.cleaned_data["region3"] = add_form.cleaned_data["name"]

            del add_form.cleaned_data["obl"]
            del add_form.cleaned_data["raion"]
            del add_form.cleaned_data["name"]

            if "sale" not in add_form.cleaned_data["action_type"]:
                del add_form.cleaned_data["exchange"]

            if "rent" in add_form.cleaned_data["action_type"]:
                if "day" in request.POST.keys() and "month" in request.POST.keys():
                    add_form.cleaned_data["period"] = "day month"
                    del add_form.cleaned_data["day"]
                    del add_form.cleaned_data["month"]
                elif "month" in request.POST.keys():
                    add_form.cleaned_data["period"] = "month"
                    del add_form.cleaned_data["month"]
                elif "day" in request.POST.keys():
                    add_form.cleaned_data["period"] = "day"
                    del add_form.cleaned_data["day"]

            if "number_of_rooms" in add_form.cleaned_data and add_form.cleaned_data["number_of_rooms"] != "":
                add_form.cleaned_data["number_of_rooms"] = int(add_form.cleaned_data["number_of_rooms"])

            del add_form.cleaned_data['agreement']

            add_form.cleaned_data['phones'] = add_form.cleaned_data['phones'].split('.')

            if '_edit' in request.POST:
                obj_id = request.POST["ObjectId"]
                ad = Advert_Users.objects.get(id=obj_id)
                # ad = Advert.objects(id=obj_id).get()
                username_bck = ad["username"]
                for key in add_form.cleaned_data:
                    if add_form.cleaned_data[key] == False or add_form.cleaned_data[key] == '' or add_form.cleaned_data[key] == None:
                        myquery = "ad.update(unset__" + key + "=1)"
                    else:
                        myquery = "ad.update(set__" + key + "=" + "add_form.cleaned_data['" + key + "'])"
                    exec(myquery)

                for key in vars(ad).keys():
                    if key not in add_form.cleaned_data.keys():
                        myquery = "ad.update(unset__" + key + "=1)"
                        exec(myquery)
       
                try:
                    original = remove_images(request.POST["stored_imgs"],request.POST["ObjectId"]);
                    if original is None:
                        original = []
                except:
                    original = []
                # return str(ad.id)
                ad.username = username_bck

            else:
               
                keys = add_form.cleaned_data.keys()
                for key in keys:
                    if add_form.cleaned_data[key] == False or add_form.cleaned_data[key] == "" or add_form.cleaned_data[key] == None:
                        del add_form.cleaned_data[key]
                
                # Advert(**add_form.cleaned_data).save()
                Advert_Users(**add_form.cleaned_data).save()
                original = []
                # doc_id = Advert()['doc_id']-1 # what is a purpose of using doc_id?
                # ad = Advert.objects(**add_form.cleaned_data).get()
                ad = Advert_Users.objects.get(**add_form.cleaned_data)
                ad.expiring_date = ad.adding_date + timedelta(days=30)
                
                ad.username = request.user.username

            thumbs = []
            medium = []

            for path in original:
                thumbs.append( path[:len(path)-4] + '-small' + path[len(path)-4:] )

            for path in original:
                medium.append( path[:len(path)-4] + '-medium' + path[len(path)-4:] )

            images = {}
            images['original'] = original
            images['thumbs'] = thumbs
            images['medium'] = medium

            ad.images = images
            ad.images_len = len(original)

            ad.cat_tab = req['cat_tab_1']
            ad.cat_type = req['cat_type_1']
            ad.save()
            return str(ad.id)

    return add_form.errors

@require_http_methods(["POST"])
@ajax
@csrf_exempt
def ajax_register(request):
    myanswer = 'Wellcome'
    if request.method == 'POST':  # If the form has been submitted...
        Registerform = RegisterForm(request.POST)  # A form bound to the POST data
        if Registerform.is_valid():  # All validation rules pass
            # Process the data in form.cleaned_data
            username = Registerform.cleaned_data["username"]
            password = Registerform.cleaned_data["password"]
            email = Registerform.cleaned_data["email"]

            errorExists = False
            if User.objects.filter(username=username).count() > 0:
                errorExists = True
                myanswer['error'] = 'error: Пользователь уже существует'
            
            elif User.objects.filter(email=email).count() > 0:
                errorExists = True
                myanswer['error'] = 'error: E-mail уже существует'

            if not errorExists:
                Profile(**Registerform.cleaned_data).save()
                User.create_user(username,password,email)

                user = authenticate(username=username, password=password)
                login(request, user)

    return myanswer

@require_http_methods(["POST"])
@ajax
@csrf_exempt
def ajax_login(request):
    myanswer = 'Wellcome'
    if request.method == 'POST':
        Registerform = RegisterForm(request.POST)
        Registerform.is_valid()
        username = Registerform.cleaned_data['username']
        try:
            user = User.objects.get(username=username)
        except:
            try:
                user = User.objects.get(email=username)
            except:
                user = None

        if user is not None:
            password = Registerform.cleaned_data['password']
            if user.check_password(password): # Redirect to a success page.
                if user.is_active:
                    user.backend = 'mongoengine.django.auth.MongoEngineBackend'
                    login(request, user)



                    if user.is_active:
                        myanswer = '<div style="margin-right: 10px"><a href="">&nbsp;</a></div><div style="margin-right: 10px"><a href="">О проекте</a></div><div style="margin-right: 200px"><a href="/support">Поддержка</a></div><!--<div style="margin-right: 10px"><a href="/user-profile">user</a></div>--><div style="margin-right: 10px"><a href="/user-profile">Профиль</a></div><div style="margin-right: 10px"><a href="/favorite-cards">Избранные</a></div><div style="margin-right: 10px"><a href="/my-cards">Мои объявления</a></div><div><a href="/logout">Выход</a></div>'
                else:
                    myanswer = 'error: Пользователь не активен (проверьте свою электронную почту, чтобы активировать аккаунт)'
            else: # Return an 'invalid login' error message.
                myanswer = 'error: Неверный пароль'
                # return HttpResponse('disabled account')
                # Return a 'disabled account' error message
        else: 
            myanswer = "error: Пользователь не существует"

    return myanswer

def mobile_auth(request):
    try:
        get_params = request.GET.copy()
        Registerform = RegisterForm(get_params)
        Registerform.is_valid()
        username = Registerform.cleaned_data['username']
   
        user = User.objects.get(username=username)
        password = Registerform.cleaned_data['password']
        if user.check_password(password) and user.is_active: # Redirect to a success page.
            user.backend = 'mongoengine.django.auth.MongoEngineBackend'
            login(request, user)

            user_profile =  Profile.objects.get(username=user.username)
            profile = json.loads(user_profile.to_json())
            userdata = json.loads(user.to_json())

            my_json = {
                'profile': profile,
                'userdata': userdata
            }
            my_answer = HttpResponse(json.dumps(my_json), content_type="application/json")
        else:
            my_answer = HttpResponse(json.dumps({'error':'incorrect password'}), content_type="application/json")
    except:
        my_answer = HttpResponse(json.dumps({'error':'incorrect user'}), content_type="application/json")

    return my_answer

def mobile_filter(request):
    get_params = request.GET.copy()
    my_obj = my_filtering(get_params)

    if 'range' in get_params:
        range_min = int(get_params['range'].split(',')[0])
        range_max = int(get_params['range'].split(',')[1])
        my_answer = HttpResponse(my_obj['ads_list2'][range_min:range_max].to_json(), content_type="application/json")

    elif 'item' in get_params:
        my_answer = HttpResponse(my_obj['ads_list2'][int(get_params['item'])].to_json(), content_type="application/json")

    elif 'page' in get_params:
        user_ads = json.loads(my_obj['ads_list1'].to_json())
        parser_ads = json.loads(my_obj['ads_list2'].to_json())

        my_json = {
            'user_ads': user_ads,
            'parser_ads': parser_ads
        }

        my_answer = HttpResponse(json.dumps(my_json), content_type="application/json")

    else:
        my_answer = HttpResponse(my_obj['ads_list2'][:10000].to_json(), content_type="application/json")

    return my_answer

@require_http_methods(['GET'])
@ajax
def get_region_in_english(region_in_russian):
    return REGION_TR[region_in_russian.GET['data']]

@require_http_methods(['GET'])
@ajax
def get_region_autocomplete2(request):
    try:
        req = request.GET['region'][:request.GET['region'].index('(')-1]
    except:
        req = request.GET['region']

    if u'область' in req:
        query_params = {'OBL': req.upper()}
        regions = Cities.objects(**query_params)
        regions_list = [region['RAION'] for region in regions]
        my_answer = [] # Capital
        for el in regions_list:
            if el not in my_answer:
                my_answer.append(el)

        return my_answer

    else:
        query_params = {'NAME': req.title()}
        regions = Cities.objects(**query_params)
        return regions[0]['RAION']


@require_http_methods(['GET'])
@ajax
def get_region_autocomplete(request):
    get_params = request.GET.copy()
    regions_list = []
    
    if "search" in get_params:
        if u' Область' in get_params["region"]:
            query_params = {'OBL': get_params["region"].upper()}
            regions_list = Cities.objects(**query_params).distinct(field="RAION")
            myanswer = sorted(regions_list)
        else:
            if u"г." in get_params["region"]:
                query_params = {
                    'NAME__icontains': get_params["region"].split()[-1], 
                    "PREF":u"г.",
                    "OBL":"",
                    # "RAION":"",
                    # "SOVET":"",
                }
                regions = Cities.objects(**query_params)
                myanswer = regions[0]["RAION"]

            else:
                query_params = {'RAION': get_params["region"]}
                regions = Cities.objects(**query_params).order_by('+NAME')

                for element in regions:
                    regions_list.append(element['PREF'] + ' ' + element['NAME'])

                myanswer = regions_list

    elif "autocomplete" in get_params:
        if u"г." in get_params["name"]:
                query_params = {
                    'NAME__icontains': get_params["name"].split()[-1], 
                    "PREF":u"г.",
                    "OBL":"",
                    # "RAION":"",
                    # "SOVET":"",
                }
                regions = Cities.objects(**query_params)
                myanswer = regions[0]["RAION"]

        else:
            regions = Cities.objects.filter(NAME__icontains=get_params["name"])
            for element in regions:
                if element["OBL"] != "":
                    found_region = element['PREF'] + ' ' + element['NAME'] + ' (' + element["OBL"].title() + ', ' + element["RAION"] + ')'
                else:
                    found_region = element['PREF'] + ' ' + element['NAME']
                regions_list.append(found_region)
            myanswer = regions_list

    elif "autocompleteStreet" in get_params:
        if u"г." in get_params["name"]:
            SOATO = Cities.objects.filter(PREF=get_params["name"].split()[0],NAME=get_params["name"].split()[-1])[0]["SOATO"]
        else:
            SOATO = Cities.objects.filter(RAION=get_params["raion"],OBL=get_params["obl"].upper(),NAME=get_params["name"].split()[-1])[0]["SOATO"]

        streets = Streets.objects.filter(SOATO=SOATO, ULICA__icontains=get_params["address"])
        try:
            myanswer = [street["NTU"].lower() + ' ' + street["ULICA"].title() for street in streets]
        except:
            myanswer = []

    return myanswer


    # try:
    #     req = request.GET['region'][:request.GET['region'].index('(')-1]
    # except:
    #     req = request.GET['region']

    # if u'область' in req:
    #     query_params = {'OBL': req.upper()}
    #     regions_list = Cities.objects(**query_params).distinct(field="RAION")
    #     return sorted(regions_list)

    # else:
    #     if req != u'Гомель' and req != u'Витебск':
    #         query_params = {'RAION': req}
    #         regions = Cities.objects(**query_params).order_by('+NAME')

    #         regions_list = []
    #         if regions.count() > 0:
    #             for element in regions:
    #                 regions_list.append(element['PREF'] + ' ' + element['NAME'])
    #             return regions_list
    #         else:
    #             regions = Cities.objects.filter(NAME__icontains=req)
    #             for element in regions:
    #                 if element["OBL"] != "":
    #                     found_region = element['PREF'] + ' ' + element['NAME'] + ' (' + element["OBL"].title() + ', ' + element["RAION"] + ')'
    #                 else:
    #                     found_region = element['PREF'] + ' ' + element['NAME']
    #                 regions_list.append(found_region)
    #             return regions_list
    #     else:
    #         # query_params = {'NAME': req.title()}
    #         # regions = Cities.objects(**query_params)
    #         # try:
    #         #     return regions[0]['RAION']
    #         # except:
    #         query_params = {
    #             'NAME__contains': req, 
    #             "PREF":u"г.",
    #             "OBL":"",
    #             # "RAION":"",
    #             "SOVET":"",
    #         }
    #         regions = Cities.objects(**query_params)
    #         region_list = regions[0]["RAION"]



    #         return region_list

@require_http_methods(['GET'])
@ajax
def get_address_autocomplete(request):
    get_params = request.GET.copy()
    SOATO = Cities.objects.filter(RAION=get_params["raion"],OBL=get_params["obl"].upper(),NAME=get_params["name"].split()[-1])[0]["SOATO"]
    streets = Streets.objects.filter(SOATO=SOATO, ULICA__icontains=get_params["address"].upper())
    return [street["ULICA"] for street in streets]
    # regions = [item['RAION'] for item in data if request.GET['region'].lower() in item['OBL'].lower()]
    

    # matching1 = [s for s in my_regions if request.GET['region'].lower() in s.lower() ]
    # region_list = []
    # for element in matching1:
    #     splited_element = element.split(',')
    #     for s in splited_element:
    #         if request.GET['region'].lower() in s.lower() and s.title() not in region_list:
    #             region_list.append(s.title())
    #             break            

    # return region_list

@require_http_methods(['GET'])
@ajax
def get_cat_type_commercial(request):
    return settings.CAT_TYPE_COMMERCIAL[request.GET['cat_tab']]

@require_http_methods(['GET'])
@ajax
def edit_user_profile(request):
    element = request.GET['element']
    action = request.GET['action']
    value = request.GET['value']

    try:
        user_profile = Profile.objects.get(username=request.user.username)
    except:
        user_profile = ProfileAgency.objects.get(username=request.user.username)

    user = User.objects.get(username=request.user.username)

    if element == 'phones':
        if action == 'add':
            user_profile.update(push__phones=value)
        elif action == 'delete':
            my_phones = user_profile['phones']
            del my_phones[int(value[16:])]
            user_profile.phones = my_phones
            user_profile.save()

    elif element == 'fullname' and any(c.isalpha() for c in value):
        user_profile.update(set__fullname=value)

    elif element == 'email':
        user_profile.update(set__email=value)
        user.update(set__email=value)

    return

@require_http_methods(['GET'])
@ajax
def ajax_get_my_cards(request):
    try:
        user =  Profile.objects.get(username=request.user.username)
    except:
        try:
            user =  ProfileAgency.objects.get(username=request.user.username)
        except:
            user = create_user_profile(request.user)

    if 'convert_currency_to' in request.GET:
        my_ads = get_my_cards(user,request.GET['convert_currency_to'] )
    else:
        my_ads = get_my_cards(user)

    try:
        favorites = user.favorites
    except:
        favorites = []
    return render(request, "adverts.html", 
        {
            'ads': my_ads,
            'myfav': favorites,
        }
    )

@require_http_methods(['GET'])
@ajax
def ajax_get_my_favorites(request):
    try:
        user =  Profile.objects.get(username=request.user.username)
    except:
        try:
            user =  ProfileAgency.objects.get(username=request.user.username)
        except:
            user = create_user_profile(request.user)

    if 'convert_currency_to' in request.GET:
        my_ads = get_my_favorites(user,request.GET['convert_currency_to'] )
    else:
        my_ads = get_my_favorites(user)

    try:
        favorites = user.favorites
    except:
        favorites = []
    return render(request, "adverts.html", 
        {
            'ads': my_ads,
            'myfav': favorites,            
        }
    )


def action_agency_by_username(request):
    obj_id = request.GET['username']
    this_user = User.objects.get(username=str(obj_id))
    if request.GET['action'] == 'True':
        this_user['is_active'] = True
        message = u'User enabled'
    else:
        this_user['is_active'] = False
        message = u'User disabled'

    this_user.save()
    return render(request, "email_sent.html",{'mys_message':message, 'redirect': False })
    # return HttpResponse(json.dumps({ this_user.username : 'enabled'}), content_type="application/json")

def enable_user(request):
    obj_id = request.GET['id']
    this_user = User.objects.get(id=str(obj_id))
    this_user['is_active'] = True
    this_user.save()
    # return render(request, "email_sent.html",{'mys_message':'Thanks for activate your account, now you can login <a href="/login">here</a>'})
    # return HttpResponse(json.dumps({ this_user.username : 'enabled'}), content_type="application/json")
    return redirect('/')

def validate_email_agency(request):
    obj_id = request.GET['id']
    this_user = User.objects.get(id=str(obj_id))
    this_profile = ProfileAgency.objects.get(username=this_user.username)
    # os.system('echo "New agency needs to be aproved: ' + str(this_user.username) + '"| mail -s "New Agency ' + this_profile.name_of_entity.encode('UTF-8') + '" gabriel_leske@hotmail.com')
    return render(request, "email_sent.html",{'mys_message':u'Ваш аккаунт отправлен на модерацию.', 'redirect': True})
    # return HttpResponse(json.dumps({ this_user.username : 'enabled'}), content_type="application/json")  

def disable_user(request):
    username = request.GET['username']
    this_user = User.objects.get(username=username)
    this_user['is_active'] = False
    this_user.save()
    return HttpResponse(json.dumps({ username : 'disabled'}), content_type="application/json") 

def make_user_admin(request):
    username = request.GET['username']
    this_user = User.objects.get(username=username)
    this_user['is_staff'] = True
    this_user['is_superuser'] = True
    this_user.save()
    return HttpResponse(json.dumps({ username : 'admin'}), content_type="application/json")

def unmake_user_admin(request):
    username = request.GET['username']
    this_user = User.objects.get(username=username)
    this_user['is_staff'] = False
    this_user['is_superuser'] = False
    this_user.save()
    return HttpResponse(json.dumps({ username : 'normal'}), content_type="application/json")


from django.core.servers.basehttp import FileWrapper
import StringIO
def yandex_txt(request,num):
    filename = 'yandex_' + num + '.txt'
    myfile = open(os.path.join(settings.STATIC_ROOT, filename))
    response = HttpResponse(FileWrapper(myfile), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response

def add_contact(request):
    this_profile = ProfileAgency.objects.get(username=request.user.username)
    return

def ef99b3aebfcd135529b9b21ae(request):
    return render(request,'ef99b3aebfcd135529b9b21ae.html')


@ajax
@require_http_methods(['POST'])
@csrf_exempt
def add_profile_image(request):   
    file_ = request.FILES['new_profile_photo']
    folder = 'profile_imgs'

    try:
        filename = str(request.user.id) + file_.name[ file_.name.rfind('.') : ]
    except:
        return 'file has not extension'

    md5_obj = md5()
    for chunk in file_.chunks():
        md5_obj.update(chunk)

    del chunk

    path = os.path.join(settings.MEDIA_ROOT, str(folder), filename)
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    with open(path, 'wb+') as destination:
        for chunk in file_.chunks():
            destination.write(chunk)
        
    img = Image.open(path)
    img.thumbnail((188,188), Image.ANTIALIAS)
    img.save(path)

    path = os.path.join(settings.STATIC_URL, settings.MEDIA_URL, str(folder), filename)

    try:
        this_profile =  Profile.objects.get(username=request.user.username)
    except:
        this_profile =  ProfileAgency.objects.get(username=request.user.username)

    this_profile.image = path
    this_profile.save()

    return (path)

@require_http_methods(['GET'])
@ajax
def edit_contact_list(request):
    action = request.GET['action']
    value = request.GET['value']
    user_profile = ProfileAgency.objects.get(username=request.user.username)

    if action == 'delete':
        my_contacts=user_profile['contacts']
        del my_contacts[int(value[18:])]
        user_profile.contacts = my_contacts
        user_profile.save()

    elif action == 'edit':
        # user_profile.update(pop__phones=value[-1:])
        pass


    return

@require_http_methods(['GET'])
@ajax
def add_new_contact(request):
    new_contact_data = request.GET.copy()
    this_profile = ProfileAgency.objects.get(username=request.user.username)
    new_contact_data["longevity"] = datetime.now()
    new_contact_data["lead_ads"] = 0
    new_contact_data["avg_transition_price"] = 0
    this_profile.update(push__contacts=new_contact_data)
    this_profile.save()
    return

@require_http_methods(['GET'])
@ajax
def add_info_agency(request):
    new_info_agency = request.GET.copy()
    this_profile = ProfileAgency.objects.get(username=request.user.username)
    for key in new_info_agency:
        myquery = "this_profile.update(set__" + key + "=" + "new_info_agency['" + key + "'])"
        exec(myquery)
    this_profile.save()
    return

@require_http_methods(['GET'])
@ajax
def get_contact_phone(request):
    contact = request.GET.copy()
    this_profile = ProfileAgency.objects.get(username=request.user.username)

    for element in this_profile['contacts']:
        if element['fullname'] == contact['fullname']:
            return element['phone']

    return 'not found'

@require_http_methods(['GET'])
@ajax
def get_cards_agency(request):
    get_params = request.GET.copy()
    obj_id = get_params['obj_id']
    
    my_profile = ProfileAgency.objects.get(id=obj_id)
    my_ads = Advert_Users.objects(username=my_profile["username"])

    query_params = {}
    query_params['username'] = my_profile["username"]

    if 'sort_order' in get_params:
        ads = Advert_Users.objects(**query_params).order_by(get_params['sort_order'])
    else:
        ads = Advert_Users.objects(**query_params)

    ads_list = list(ads)

    if "convert_currency_to" in get_params and not get_params['convert_currency_to'].strip() == "":
        _to_curr = get_params['convert_currency_to']

        for ad in ads_list:
            ad.price = price_convert(float(ad.price), ad.currency, _to_curr)
            ad.currency = _to_curr

    return render(request, "adverts.html", 
        {
            'ads': ads_list,           
        }
    )
