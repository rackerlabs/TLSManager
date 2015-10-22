from django.template import loader, Context
from django.template import RequestContext
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.core.context_processors import csrf
from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.db import connection
from django.db.models import Q
from django.db.models import Max
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.utils import timezone
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Contact, Product, Endpoint, TestResult, Defect, Setting
from errno import ECONNREFUSED
import logging
import requests
import simplejson
import threading
import multiprocessing
from subprocess import Popen, PIPE, STDOUT
import datetime
import OpenSSL
import socket
import random
import pytz
import time
import sys
import ast
import os
import parse_ssllabs

logger = logging.getLogger(__name__)
lines_per_page = 15


def list_test_results(request, page2return2='0'):
    errors = []
    page_data = {}
    page_direction = 'Next'
    current_page = '0'
    endpoint_tr_tuples = []
    current_sort_order = 'url'

    check_good_number(page2return2)
    if page2return2 != '0':
        current_page = str(int(page2return2) - 1)

    if request.method == 'POST':
        if not request.POST.get('page_to_display', ''):
            current_page = '0'
        else:
            check_good_number(request.POST['page_to_display'])
            current_page = request.POST['page_to_display']

        if not request.POST.get('page_direction', ''):
            page_direction = 'Next'
        else:
            check_valid_size(request.POST['page_direction'])
            page_direction = request.POST['page_direction']

        if not request.POST.get('current_sort_order', ''):
            current_sort_order = 'url'
        else:
            check_valid_size(request.POST['current_sort_order'])
            current_sort_order = request.POST['current_sort_order']

        if request.POST.get('url', ''):  # url sort button pressed
            current_sort_order = 'url'
            page_direction = 'Next'
            current_page = '0'
            endpoints_all = Endpoint.objects.all().order_by('url')
            endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
        elif request.POST.get('product', ''):  # product sort button pressed
            current_sort_order = 'product'
            page_direction = 'Next'
            current_page = '0'
            endpoints_all = Endpoint.objects.all().order_by('product__name')
            endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
        elif request.POST.get('last_scan_date', ''):  # last_scan_date sort
            current_sort_order = 'last_scan_date'
            page_direction = 'Next'
            current_page = '0'
            endpoints_all = Endpoint.objects.all().order_by('product__name')
            endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
            endpoint_tr_tuples = sort_by_time(endpoint_tr_tuples)
        elif request.POST.get('score', ''):  # score sort button pressed
            current_sort_order = 'score'
            page_direction = 'Next'
            current_page = '0'
            endpoints_all = Endpoint.objects.all().order_by('product__name')
            endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
            endpoint_tr_tuples = sort_by_score(endpoint_tr_tuples)
        else:  # Next or Prev button cases
            endpoint_tr_tuples = create_tuple_set_for_sort_order(
                                                            current_sort_order)
    else:  # method GET
        endpoints_all = Endpoint.objects.all().order_by('url')
        #endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
        # if coming from a Return from the details page
        if 'current_sort_order' in request.COOKIES:
            current_sort_order = request.COOKIES['current_sort_order']
        endpoint_tr_tuples = create_tuple_set_for_sort_order(
                                                            current_sort_order)

    endpoint_tr_tuple_page = paginate_list(endpoint_tr_tuples,
                                           page_data,
                                           current_page,
                                           page_direction)

    page_data['errors'] = errors
    page_data['endpoint_tr_tuples'] = endpoint_tr_tuple_page
    page_data['current_sort_order'] = current_sort_order

    response = render_to_response('test_results.html',
                                  page_data, RequestContext(request))
    response.set_cookie('current_sort_order', current_sort_order)
    return response


def create_tuple_set_for_sort_order(current_sort_order):
    if current_sort_order == 'url':
        endpoints_all = Endpoint.objects.all().order_by('url')
        endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
    elif current_sort_order == 'product':
        endpoints_all = Endpoint.objects.all().order_by('product__name')
        endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
    elif current_sort_order == 'last_scan_date':
        endpoints_all = Endpoint.objects.all().order_by('product__name')
        endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
        endpoint_tr_tuples = sort_by_time(endpoint_tr_tuples)
    elif current_sort_order == 'score':
        endpoints_all = Endpoint.objects.all().order_by('product__name')
        endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
        endpoint_tr_tuples = sort_by_score(endpoint_tr_tuples)
    else:
        endpoints_all = Endpoint.objects.all().order_by('url')
        endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
    return endpoint_tr_tuples


# endpoint_tr_tuples is a list of tuples
# each tuple is composed of an endpoint, its last test result
# and the next to last test result.
def create_endpoint_last_tr_tuples(endpoints_all):
    timezone.activate(pytz.timezone('America/Chicago'))

    endpoint_tr_tuples = []
    for endpoint in endpoints_all:
        tr_lst = endpoint.test_results.all().order_by('-time')  # don't change
        if len(tr_lst) > 1:
            endpoint_tr_tuples.append((endpoint, tr_lst[0], tr_lst[1]))
            logger.info('=== endpoint=' + str(endpoint.url))
            logger.info('-------------')
        elif len(tr_lst) > 0:
            endpoint_tr_tuples.append((endpoint, tr_lst[0], None))
        else:
            endpoint_tr_tuples.append((endpoint, None, None))
    return endpoint_tr_tuples


# endpoint_tr_tuples is a list of tuples
# each tuple is composed of an endpoint, its last test result
# and the next to last test result. This function sort by the test result time
def sort_by_time(endpoint_tr_tuples):
    utc = pytz.utc
    epoch_time = datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=utc)
    endpoint_tr_tuples.sort(key=lambda tup:
                            (epoch_time if tup[1] is None else tup[1].time))
    endpoint_tr_tuples.reverse()
    return endpoint_tr_tuples


# endpoint_tr_tuples is a list of tuples
# each tuple is composed of an endpoint, its last test result
# and the next to last test result. This function sort by the test result score
def sort_by_score(endpoint_tr_tuples):
    sorted_by_second = sorted(endpoint_tr_tuples, key=lambda tup:
                              ('' if tup[1] is None else tup[1].score))
    sorted_by_second.reverse()
    return sorted_by_second


def paginate_list(list_to_paginate, page_data, current_page, page_direction):
    p = Paginator(list_to_paginate, lines_per_page)
    page_2_display = p.page(1)
    page_data['first_page'] = None
    page_data['last_page'] = None
    if current_page == '0':  # first time displaying search result
        if p.page(1).count > 0:  # there are rows to display
            page_2_display = p.page(1)
            page_data['page_to_display'] = 1
    else:
        if page_direction == 'Next':
            if p.page(int(current_page)).has_next():
                next_page_number = p.page(
                    int(current_page)).next_page_number()
                page_2_display = p.page(next_page_number)
                page_data['page_to_display'] = next_page_number
        else:
            if p.page(int(current_page)).has_previous():
                prev_page_number = p.page(
                    int(current_page)).previous_page_number()
                page_2_display = p.page(prev_page_number)
                page_data['page_to_display'] = prev_page_number

    if p.num_pages == 1:  # only a single page of rows so do not display arrows
        page_data['first_page'] = page_data['last_page'] = True
    else:
        if not page_2_display.has_previous():
            page_data['first_page'] = True
        else:
            page_data['first_page'] = False
        if not page_2_display.has_next():
            page_data['last_page'] = True
        else:
            page_data['last_page'] = False

    list_page = page_2_display.object_list
    return list_page


def product_results(request, product_id):
    check_good_number(product_id)
    page_data = {}
    last_endpoint_result = Endpoint.objects.annotate(Max('testresult__id')) \
        .filter(product_id=product_id, testresult__id__max__isnull=False) \
        .values('testresult__id__max')
    endpoint_results = Endpoint.objects.filter(testresult__id__in=last_endpoint_result) \
        .values('url', 'id', 'testresult__id', 'testresult__score', 'testresult__time')
    page_data['endpoint_results'] = endpoint_results
    return render_to_response('product_results.html', page_data, RequestContext(request))


def tab(request):
    page_data = {}
    return render_to_response('scrollable_table.html',
                              page_data, RequestContext(request))


def test_result_details(request, result_id, page2return2):
    check_good_number(result_id)
    check_good_number(page2return2)
    errors = []
    page_data = {}
    
    result = TestResult.objects.get(id=result_id)
    defects = result.defects.all()
    the_endpoint = result.the_endpoint
    hist_results = list(TestResult.objects.filter(the_endpoint=the_endpoint).order_by('-time'))
    del hist_results[0]
    
    product = the_endpoint.product
    contact = product.contacts.all()[0]
    page_data['errors'] = errors
    page_data['result'] = result
    page_data['hist_results'] = hist_results
    page_data['contact'] = contact
    page_data['product'] = product
    page_data['defects'] = defects
    page_data['page2return2'] = page2return2
    return render_to_response('test_details.html',
                              page_data, RequestContext(request))


# invoked by AJAX to send email from test details form
def send_email_to_contact(request):
    result_id = request.POST['result_id']
    check_good_number(result_id)
    result = TestResult.objects.get(id=result_id)
    defects = result.defects.all()
    the_endpoint = result.the_endpoint
    product = the_endpoint.product
    contacts = product.contacts.all()
    addresses = []
    for contact in contacts:
        addresses.append(contact.email)
    add_default_product_addresses(addresses)
    default_product = Product.objects.get(id=1)
    subject = default_product.name + ": Test results for " \
        + product.name \
        + "(" + the_endpoint.url + ")  - " \
        + str(result.time)
    t = loader.get_template('report_for_product_email.html')
    c = Context({'defects': defects,
                'product': product.name,
                 'url': the_endpoint.url, 'time': result.time})
    message = t.render(c)

    from_address = Setting.objects.all()[0].default_email
    send_mail_python(subject, message, from_address, addresses)
    return HttpResponse(
        simplejson.dumps({'result_id': result_id}),
        content_type="application/json")


def add_default_product_addresses(addresses):
    default_product = Product.objects.get(id=1)
    contacts = default_product.contacts.all()
    for contact in contacts:
        if contact.email not in addresses:
            addresses.append(contact.email)


def summary_report(request):
    page_data = {}
    score_count = get_score_count()
    page_data['score_count'] = score_count
    return render_to_response(
        'summary_report.html', page_data, RequestContext(request))


def product_overview(request):
    page_data = {}
    product_scores = get_product_scores()
    page_data['product_scores'] = product_scores
    return render_to_response(
        'product_overview.html', page_data, RequestContext(request))


def get_product_scores():
    last_endpoint_test = Endpoint.objects.annotate(Max('testresult__id')) \
        .filter(testresult__id__max__isnull=False) \
        .values('testresult__id__max')
    '''
    # Returns data per endpoint.
    TestResult.objects.filter(id__in=last_endpoint_test) \
        .values('score','time','endpoint__url','endpoint__product__name')
    '''

    # Returns data per product 
    product_scores = TestResult.objects.filter(id__in=last_endpoint_test) \
        .values('endpoint__product__name', 'endpoint__product__id') \
        .annotate(Max('score'))

    return product_scores


def cert_report(request):
    page_data = {}
    page_data['about_to_expire_endpoints'] = get_certs_about_to_expire()
    return render_to_response(
        'cert_report.html', page_data, RequestContext(request))


def get_score_count():
    test_results = TestResult.objects.all().order_by('the_endpoint', '-time')
    latest_test_result = []
    prev_result_endpoint = ''
    for result in test_results:
        if result.the_endpoint == prev_result_endpoint:
            continue
        else:
            latest_test_result.append(result)
            prev_result_endpoint = result.the_endpoint

    score_count = {'A': 0, 'Aplus': 0, 'Aminus': 0, 'B': 0, 'C': 0, 'D': 0,
                   'E': 0, 'M': 0, 'N': 0, 'T': 0, 'F': 0}
    for tr in latest_test_result:
        if tr.score == 'A':
            score_count['A'] += 1
        elif tr.score == 'A+':
            score_count['Aplus'] += 1
        elif tr.score == 'A-':
            score_count['Aminus'] += 1
        elif tr.score == 'B':
            score_count['B'] += 1
        elif tr.score == 'C':
            score_count['C'] += 1
        elif tr.score == 'D':
            score_count['D'] += 1
        elif tr.score == 'E':
            score_count['E'] += 1
        elif tr.score == 'M':
            score_count['M'] += 1
        elif tr.score == 'N':
            score_count['N'] += 1
        elif tr.score == 'T':
            score_count['T'] += 1
        elif tr.score == 'F':
            score_count['F'] += 1
        else:
            logger.info('unknown score found: ' + tr.score)
    return score_count


# this processes the delete request from the change test results details page
@login_required(login_url='/login/')
def delete_test_result_details(request):
    result_id = request.GET.get('result_id', None)
    check_good_number(result_id)
    result = TestResult.objects.get(id=result_id)
    result.delete()
    return HttpResponseRedirect("/dashboard")


# this view handles an AJAX request to populate the Change URL screen
def get_change_url_details(request):
    endpoint_id = request.POST.get('endpoint_id', None)
    check_good_number(endpoint_id)
    endpoint = Endpoint.objects.get(id=endpoint_id)
    product = endpoint.product
    return HttpResponse(
            simplejson.dumps({'product_name': product.name,
                             'endpoint_id': endpoint_id}),
            content_type="application/json")


# change URL
@login_required(login_url='/login/')
def change_url_details(request):
    errors = []
    page_data = {}
    endpoints = Endpoint.objects.all()
    page_data['errors'] = errors
    page_data['endpoints'] = endpoints
    return render_to_response(
        'change_details.html', page_data, RequestContext(request))


# this processes the AJAX delete request from the change URL details page
@login_required(login_url='/login/')
def delete_url_details(request):
    endpoint_id = request.GET.get('endpoint_id', None)
    check_good_number(endpoint_id)
    endpoint = Endpoint.objects.get(id=endpoint_id)
    endpoint.delete()
    return HttpResponse(
            simplejson.dumps({'message': 'success'}),
            content_type="application/json")


@login_required(login_url='/login/')
def add_contact(request):
    errors = []
    page_data = {'errors': errors}
    if request.method == 'POST':
        if not request.POST.get('firstname', ''):
            errors.append('First name is required')
        else:
            check_valid_size(request.POST['firstname'])
            page_data['firstname'] = request.POST['firstname']
    
        if not request.POST.get('lastname', ''):
            errors.append('Last name is required')
        else:
            check_valid_size(request.POST['lastname'])
            page_data['lastname'] = request.POST['lastname']
    
        if not request.POST.get('email', ''):
            errors.append('Email is required')
        else:
            if is_valid_email(request.POST['email']):
                # check if already exists
                contact = Contact.objects.filter(email=request.POST['email'].strip())
                if contact:
                    errors.append('Email already exists')
            else:
                errors.append('Invalid email')
            page_data['email'] = request.POST['email']

        if not errors:
            contact = Contact(
                first_name=request.POST['firstname'],
                last_name=request.POST['lastname'],
                email=request.POST['email'])
            contact.save()
            errors.append('Contact was saved')
            page_data['firstname'] = ''
            page_data['lastname'] = ''
            page_data['email'] = ''
    return render_to_response(
        'add_contact.html', page_data, RequestContext(request))


@login_required(login_url='/login/')
def change_contact(request):
    errors = []
    page_data = {}
    contacts = list(Contact.objects.all().order_by('email'))
    page_data['errors'] = errors
    page_data['contacts'] = contacts
    return render_to_response(
        'change_contact.html', page_data, RequestContext(request))


# this view handles the AJAX request to update the data
# when the user changes the fields
def update_contact(request):
    errors = []
    page_data = {}
    if request.method == 'POST':
        if not request.POST.get('contact_id', ''):
            raise Http404
        else:
            check_good_number(request.POST['contact_id'])

        if not request.POST.get('firstname', ''):
            errors.append('First name is required')
        else:
            check_valid_size(request.POST['firstname'])
            page_data['firstname'] = request.POST['firstname']

        if not request.POST.get('lastname', ''):
            errors.append('Last name is required')
        else:
            check_valid_size(request.POST['lastname'])
            page_data['lastname'] = request.POST['lastname']

        if not errors:
            contact_id = request.POST.get('contact_id', None)
            contact = Contact.objects.get(id=contact_id)
            contact.first_name = request.POST.get('firstname', None)
            contact.last_name = request.POST.get('lastname', None)
            contact.save()

    return HttpResponse(
        simplejson.dumps(
            {}), content_type="application/json")


# this view handles an AJAX request to populate the Change URL screen
def get_change_contact(request):
    check_good_number(request.GET['contact_id'])
    contact_id = request.GET.get('contact_id', None)
    contact = Contact.objects.get(id=contact_id)
    return HttpResponse(
        simplejson.dumps({'firstname': contact.first_name,
                         'lastname': contact.last_name}),
        content_type="application/json")


# this processes the delete contact from the change contact page
@login_required(login_url='/login/')
def delete_contact(request):
    check_good_number(request.GET['contact_id'])
    contact_id = request.GET.get('contact_id', None)
    contact = Contact.objects.get(id=contact_id)
    contact.delete()
    return HttpResponseRedirect("/changeContact")


@login_required(login_url='/login/')
def add_product(request):
    errors = []
    contacts = Contact.objects.all()
    page_data = {'errors': errors, 'contacts': contacts}
    if request.method == 'POST':
        if not request.POST.get('name', ''):
            errors.append('Product name is required')
        else:
            check_valid_size(request.POST['name'])
            # check if already in db
            product = Product.objects.get(name=request.POST['name'])
            if product:
                errors.append('Product already exists')
            page_data['name'] = request.POST['name']
        if not errors:
            product = Product(name=request.POST['name'])
            product.save()
            selected_contact = get_object_or_404(
                Contact, pk=request.POST.get('contacts'))
            product.contacts.add(selected_contact)
            errors.append('Product was saved')
    return render_to_response('add_product.html',
                              page_data, RequestContext(request))


@login_required(login_url='/login/')
def change_product(request):
    errors = []
    page_data = {}
    products = list(Product.objects.all().order_by('name'))
    contacts = list(Contact.objects.all().order_by('email'))
    page_data['errors'] = errors
    page_data['contacts'] = contacts
    page_data['products'] = products
    return render_to_response('change_product.html',
                              page_data, RequestContext(request))


# this view handles the AJAX request to update the data
# when the user changes the fields
def update_product(request):
    errors = []
    page_data = {}
    if request.is_ajax():
        if request.method == 'POST':
            body = request.body
            
            product_id = request.POST.get('product_id', '')
            check_good_number(product_id)
            
            contact_id = request.POST.get('contact_id', '')
            check_good_number(product_id)

            product = Product.objects.get(id=product_id)
            if not product:
                errors.append('Invalid product id supplied')
            contact = Contact.objects.get(id=contact_id)
            if not contact:
                errors.append('Invalid contact id supplied')
        
            if not errors:
                product.contacts.add(contact)
                product.save()
                errors.append('Product was saved')
        
        else: # GET request received
            raise Http404
    else: # not ajax
        raise Http404
        
    page_data['errors'] = errors
    return HttpResponse(
        simplejson.dumps(
            {}), content_type="application/json")


@login_required(login_url='/login/')
def add_url(request):
    errors = []
    products = Product.objects.all()
    page_data = {'errors': errors, 'products': products}
    if request.method == 'POST':
        if not request.POST.get('url', ''):
            errors.append('URL is required')
        else:
            if is_valid_url(request.POST['url']):
                url = request.POST['url'].strip()
                if not url.startswith('https'):
                    url = url.replace('http', 'https')
                
                idx = url.find("/", 8)
                if idx != -1:
                    cleanUrl = url[0: idx]
                else:
                    cleanUrl = url            
                page_data['url'] = cleanUrl
                
                # if duplicate, ignore
                objs = Endpoint.objects.filter(url=cleanUrl)
                if len(objs) > 0:
                    errors.append('Duplicate url')
            else:
                errors.append('Invalid url')
              
        if not errors:
            endpoint = Endpoint(url=cleanUrl)
            selected_product = get_object_or_404(
                Product, pk=request.POST.get('products'))
            endpoint.product = selected_product
            endpoint.save()
            errors.append('URL was saved')
    return render_to_response('add_url.html',
                              page_data, RequestContext(request))


@login_required(login_url='/login/')
def search_contact(request):
    errors = []
    contacts = []
    page_data = {}
    if request.method == 'POST':
        if not request.POST.get('search_string', ''):
            errors.append('Search string is required')
        else:
            check_valid_size(request.POST['search_string'])
            page_data['search_string'] = request.POST['search_string']
        if not errors:
            if request.POST['search_string'].strip() == r'*':
                contacts = list(Contact.objects.all().order_by('email'))
            else:
                contacts = list(
                    Contact.objects.filter(
                        Q(email__icontains=page_data['search_string']) |
                        Q(first_name__icontains=page_data['search_string']) |
                        Q(last_name__icontains=page_data[
                            'search_string'])).order_by('email'))
        page_data['errors'] = errors
        page_data['contacts'] = contacts
    return render_to_response('search_contact.html',
                              page_data, RequestContext(request))


@login_required(login_url='/login/')
def search_product(request):
    errors = []
    products = []
    page_data = {}
    if request.method == 'POST':
        if not request.POST.get('search_string', ''):
            errors.append('Search string is required')
        else:
            check_valid_size(request.POST['search_string'])
            page_data['search_string'] = request.POST['search_string']
        if not errors:
            if request.POST['search_string'].strip() == r'*':
                products = list(Product.objects.all().order_by('name'))
            else:
                products = list(
                    Product.objects.filter(name__icontains=page_data[
                        'search_string']).order_by('name'))
        page_data['errors'] = errors
        page_data['products'] = products
    return render_to_response('search_product.html',
                              page_data, RequestContext(request))


def search_url(request):
    errors = []
    endpoints = []
    page_data = {}
    page_direction = 'Next'
    page_data['first_page'] = True
    page_data['last_page'] = True
    if request.method == 'POST':
        if not request.POST.get('search_string', ''):
            errors.append('Search string is required')
        else:
            check_valid_size(request.POST['search_string'])
            page_data['search_string'] = request.POST['search_string']

        if not request.POST.get('page_to_display', ''):
            current_page = '0'
        else:
            check_good_number(request.POST['page_to_display'])
            current_page = request.POST['page_to_display']

        if not request.POST.get('page_direction', ''):
            page_direction = 'Next'
        else:
            check_valid_size(request.POST['page_direction'])
            page_direction = request.POST['page_direction']

        if not errors:
            if request.POST['search_string'].strip() == r'*':
                endpoints = list(Endpoint.objects.all().order_by('url'))
            else:
                endpoints = list(
                    Endpoint.objects.filter(url__icontains=page_data[
                        'search_string']).order_by('url'))

            endpoints = paginate_list(endpoints, page_data,
                                      current_page, page_direction)

        page_data['errors'] = errors
        page_data['endpoints'] = endpoints
    return render_to_response('search_url.html',
                              page_data, RequestContext(request))


@login_required(login_url='/login/')
def configure(request):
    errors = []
    page_data = {}
    config = Setting.objects.all()[0]
    contacts = Contact.objects.all()
    if request.method == 'POST':
        if not request.POST.get('default_email', ''):
            errors.append('Email is required')
        else:
            if is_valid_email(request.POST['default_email']):
                config.default_email = request.POST['default_email']
            else:
                errors.append('Invalid email')

        check_valid_size(request.POST['scan_enabled'])
        if request.POST['scan_enabled'] == 'True':
            config.scan_enabled = 1
        else:
            config.scan_enabled = 0

        check_valid_size(request.POST['scan_frequency'])
        if request.POST['scan_frequency'] == 'Daily':
            config.default_scan_frequency = 1
        elif request.POST['scan_frequency'] == 'Every_2_days':
            config.default_scan_frequency = 2
        elif request.POST['scan_frequency'] == 'Weekly':
            config.default_scan_frequency = 3
        elif request.POST['scan_frequency'] == 'Monthly':
            config.default_scan_frequency = 4
        elif request.POST['scan_frequency'] == 'Quarterly':
            config.default_scan_frequency = 5
        elif request.POST['scan_frequency'] == 'Yearly':
            config.default_scan_frequency = 6
        else:
            config.default_scan_frequency = 1

        check_valid_size(request.POST['scan_score_threshold'])
        config.scan_score_threshold = request.POST['scan_score_threshold']

        check_valid_size(request.POST['auto_purge'])
        config.auto_purge = request.POST['auto_purge']

        check_valid_size(request.POST['test_retention_period'])
        if request.POST['test_retention_period'] == '1_Month':
            config.test_retention_period = 1
        elif request.POST['test_retention_period'] == '1_Quarter':
            config.test_retention_period = 2
        elif request.POST['test_retention_period'] == '1_Year':
            config.test_retention_period = 3
        elif request.POST['test_retention_period'] == 'Forever':
            config.test_retention_period = 4
        else:
            config.test_retention_period = 4
        config.save()
    page_data['errors'] = errors
    page_data['config'] = config
    page_data['contacts'] = contacts
    return render_to_response('settings.html',
                              page_data, RequestContext(request))


def purge_old_tests():
    today = datetime.datetime.now()
    one_year = datetime.timedelta(days=365)
    one_year_ago = today - one_year
    logger.info('=== purging...')
    logger.info('date one year ago=' + str(one_year_ago))
    TestResult.objects.filter(time__lte=one_year_ago).delete()


# this function exists to prevent multiple workers from
# starting multiple scans
def is_already_scanned(semaphore_type, interval_in_secs):
    time.sleep(random.randint(1, 30))

    # if file exists
    if os.path.isfile(semaphore_type):
        check = os.stat(semaphore_type)
        now = time.time()
        check_time = check.st_ctime
        logger.info(' now = ' + str(now) + '   check time=' + str(check_time))
        if now - check_time < interval_in_secs:
            logger.info(
             'File changed recently so scanning was already done. Returning')
            return True

    logger.info('File was changed a long time ago so OK to start scanning again')
    semaphore = open(semaphore_type, 'w')
    semaphore.close()
    return False


def start_periodic_scans():
    logger.info('starting periodic scans')

    start_time = None
    while True:
        config = Setting.objects.all()[0]
        if config.scan_enabled:
            endpoints = Endpoint.objects.all()
            start_time = datetime.datetime.now()
            for endpoint in endpoints:
                logger.info('starting scan of ' + str(endpoint))
                p = threading.Thread(
                    target=scanner_worker, args=(endpoint.id,))
                logger.info('before start')
                p.start()
                p.join()
                logger.info('good night')
                sleep_while_pinging(3)
                logger.info('after sleep 3')
            end_time = datetime.datetime.now()
            delta_t = end_time - start_time
            secs = delta_t.seconds
            logger.info('scan cycle took ' + str(secs) + ' seconds')
            purge_old_tests()
        else:
            logger.info('Background scan is disabled')
            sleep_while_pinging(60)
            continue
        time_to_scan_list = (end_time - start_time).total_seconds()
        if config.default_scan_frequency == 1:
            logger.info('sleeping for a day')
            if time_to_scan_list < 86400:
                sleep_while_pinging(86400 - time_to_scan_list)
        elif config.default_scan_frequency == 2:
            logger.info('sleeping for 2 days')
            if time_to_scan_list < 2*86400:
                sleep_while_pinging(2*86400 - time_to_scan_list)
        elif config.default_scan_frequency == 3:
            logger.info('sleeping for a week')
            if time_to_scan_list < 7*86400:
                sleep_while_pinging(7*86400 - time_to_scan_list)
        elif config.default_scan_frequency == 4:
            logger.info('sleeping for a month')
            sleep_while_pinging(30*86400)
        elif config.default_scan_frequency == 5:
            sleep_while_pinging(3*30*86400)
        elif config.default_scan_frequency == 6:
            sleep_while_pinging(365*86400)
        else:
            sleep_while_pinging(86400)  # wait a day


def kickoff_periodic_scans():
    t = threading.Thread(target=start_periodic_scans, args=())
    t.start()


# this was created to keep MySQL connection alive
def sleep_while_pinging(seconds):
    cursor = connection.cursor()
    cursor.execute('select 1 from endpoints_setting')

    if seconds < 3600:  # if sleep time less than 1 hour
        time.sleep(seconds)
        return

    hours_to_sleep = float(seconds) / float(3600)
    total_hours_slept = 0.0
    while True:
        time.sleep(3600)  # sleep 1 hour
        cursor = connection.cursor()
        cursor.execute('select 1 from endpoints_setting')
        total_hours_slept += 1.0
        if total_hours_slept > hours_to_sleep:
            return


# this view handles the Scan Now AJAX submission
def submit_for_scan(request):
    logger.info('inside submit_for_scan ')
    check_good_number(request.GET['endpoint_id'])
    endpoint_id = request.GET.get('endpoint_id', None)
    p = multiprocessing.Process(target=scanner_worker, args=(endpoint_id,))
    p.start()
    return HttpResponse(
        simplejson.dumps(
            {'endpoint_id': endpoint_id}), content_type="application/json")


def scanner_worker(endpoint_id):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    import django
    django.setup()
    from endpoints.models import TestResult, Endpoint

    PACKAGE_ROOT = getattr(settings, 'PACKAGE_ROOT', '')
    print '-->' + PACKAGE_ROOT + " Processing %s" % (endpoint_id)
    endpoint = Endpoint.objects.get(id=endpoint_id)
    url = endpoint.url
    p = Popen([
              PACKAGE_ROOT + "/ssllabs-scan", 
              "--ignore-mismatch=true", 
              url],
              stdout=PIPE)
    print 'url=' + url
    scan_result_out = p.stdout.read()
    if scan_result_out:
        scan_result_out = scan_result_out.replace(r'\u003d', '=')
        data = simplejson.loads(scan_result_out)
        extracted = parse_ssllabs.extractScanInfo(data)
        if extracted:
            score = extracted[0]
            flaws = extracted[1]
            expiry_date = extracted[2]
            tr = TestResult(
                            time=datetime.datetime.now(),
                            score=score, the_endpoint=endpoint)
            tr.save()
            endpoint.test_results.add(tr)
            endpoint.expiry_date = expiry_date
            endpoint.save()
            for flaw in flaws:
                d = Defect(description=flaw)
                d.save()
                tr.defects.add(d)
    print " Scanning %s \tDONE" % url


def send_report_email():
    logger.info('Inside send_report_email')
    address = Setting.objects.all()[0].default_email
    score_count = get_score_count()
    endpoints_all = Endpoint.objects.all().order_by('url')
    endpoint_tr_tuples = create_endpoint_last_tr_tuples(endpoints_all)
    score_tuples = []
    b_score_tuples = []
    c_score_tuples = []
    d_score_tuples = []
    f_score_tuples = []
    for tuple in endpoint_tr_tuples:
        (ep, tr, tr_prev) = tuple
        if tr is not None:
            if tr.score == 'B':
                b_score_tuples.append(tuple)
            elif tr.score == 'C':
                c_score_tuples.append(tuple)
            elif tr.score == 'D':
                d_score_tuples.append(tuple)
            elif tr.score == 'F':
                f_score_tuples.append(tuple)

    score_tuples = f_score_tuples + d_score_tuples + c_score_tuples + b_score_tuples
    
    #global about_to_expire_endpoints
    about_to_expire_endpoints = get_certs_about_to_expire()

    default_product = Product.objects.get(id=1)
    subject = default_product.name + ': URLs with Failing TLS Scores'
    addresses = []
    add_default_product_addresses(addresses)
    t = loader.get_template('report_email.html')
    c = Context(
        {'endpoint_tr_tuples': score_tuples,
         'score_count': score_count,
         'about_to_expire_endpoints': about_to_expire_endpoints})
    message = t.render(c)
    send_mail_python(subject, message, address, addresses)
    logger.info('------ to addresses --------')
    for addr in addresses:
        logger.info(addr)


def get_certs_about_to_expire():
    about_to_expire_endpoints = {}
    endpoints_all = Endpoint.objects.all()
    for endpoint in endpoints_all:
        expiry_date = endpoint.expiry_date
        if expiry_date:
            today = datetime.datetime.now()
            delta_t = expiry_date - today.date()
            days_to_expiry = delta_t.days
            if days_to_expiry < 0:
                days_to_expiry = 0
            if days_to_expiry < 90:
                logger.info('about to expire=' + str(days_to_expiry))
                about_to_expire_endpoints[endpoint.url] = days_to_expiry
    return about_to_expire_endpoints


def kickoff_periodic_reporting():
    t = threading.Thread(target=start_periodic_reporting, args=())
    t.start()


def send_mail_python(subject, message, from_address, to_addresses):
    logger.info("Entering send_mail_python")
    import smtplib
    from email.mime.text import MIMEText

    # Create a text/plain message
    msg = MIMEText(message, 'html')

    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_addresses[0]

    EMAIL_HOST = getattr(settings, 'EMAIL_HOST', '')
    EMAIL_PORT = getattr(settings, 'EMAIL_PORT', '25')
    s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    s.sendmail(from_address, to_addresses, msg.as_string())
    s.quit()
    logger.info("Exiting send_mail_python - email sent")


# This function kicks off the scan and reporting threads
# The semaphore file is deleted in the gunicorn startup script
def init_threads(request):
    # if file exists threads already started
    if os.path.isfile("semaphore"):
        return HttpResponseRedirect('/')

    logger.info('Semaphore file does not exist so start threads')
    kickoff_periodic_scans()
    kickoff_periodic_reporting()

    semaphore = open("semaphore", 'w')
    semaphore.close()
    return HttpResponseRedirect('/')


def start_periodic_reporting():
    logger.info('Starting periodic reporting')
    while True:
        logger.info('Reporting while loop - starting thread...')
        p = threading.Thread(target=send_report_email, args=())
        p.start()
        p.join
        now = datetime.datetime.now()
        logger.info(
            'Periodic reporting ' + str(now) + ' hour=' + str(now.hour))
        
        logger.info('Reporting - sleeping ...')
        time.sleep(86400)  # 1 day
        logger.info('Reporting - waking up')


@login_required(login_url='/login/')
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')


def is_valid_email(email):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    check_valid_size(email)
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def is_valid_url(url):
    from django.core.validators import URLValidator
    from django.core.exceptions import ValidationError
    check_valid_size(url)
    validate = URLValidator()
    try:
        validate(url)
        return True
    except ValidationError:
        return False


def check_valid_size(data):
    MAX_DATA_SIZE = 500
    if not data:
        raise Http404
    if len(data) > MAX_DATA_SIZE:
        raise Http404


def check_good_number(data):
    check_valid_size(data)
    if not str(data).isdigit():
        raise Http404
