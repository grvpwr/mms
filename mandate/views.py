from django.shortcuts import render
from .forms import *
from .models import *
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseNotFound, Http404
from django.db.models import Q, Subquery
import tempfile, zipfile
from datetime import datetime, date
from extras.mandate_image import makeJpg, makeTif
from extras.mandate_xml import makeXml
from extras.xml2csv import zip2dict
from djangoproject.settings import MEDIA_URL
from django.core.paginator import Paginator
from django.core import serializers
from .custom_functions import *
from django.utils.datastructures import MultiValueDictKeyError
from django.contrib.auth.decorators import login_not_required
from django.views.decorators.csrf import csrf_exempt
from .crypto import call_java_for_crypto


def index(request):
	base_queryset = get_mandate_queryset(request.user.userextended.office)
	mandates = base_queryset.exclude(mandate_image__exact = '')
	mandates_pending_image = base_queryset.filter(mandate_image__exact = '').order_by('id')
	context = {"mandates": mandates, "mandates_pending_image": mandates_pending_image}
	
	context['new'] = mandates.filter(init_req_flag=True).count()
	
	subquery = Presentation.objects.exclude(npci_upload_time = None).values("id")
	context['npci'] = mandates.filter(presentation__npci_status = None, presentation__npci_upload_error = None, presentation__id__in=Subquery(subquery)).count()
	
	context['rejected'] = mandates.filter(presentation__npci_status='Rejected').count()
	context['rejected_no_response'] = mandates.filter(presentation__npci_status='Rejected', presentation__npci_reason_code__exact=None).count()
	context['active'] = mandates.filter(presentation__npci_status='Active').count()

	context['cancelation_req'] = Presentation.objects.filter(cancel_req_flg=True, cancel_flg=False, id__in=base_queryset.values_list('presentation__id', flat=True))

	return render(request, "mandate/index.html", context)


def paginate(request, pagenum):
	print(request.GET)
	form = FilterMandates(request.GET)

	base_queryset = get_mandate_queryset(request.user.userextended.office)
	mandates = base_queryset.exclude(mandate_image__isnull=True).exclude(mandate_image__exact = '')

	if 'status' in request.GET.keys() and request.GET['status']:
		status = request.GET['status']
		if status == 'Active' or status == 'Rejected':
			mandates = mandates.filter(presentation__npci_status__exact = request.GET['status'])
		elif status == 'new':
			mandates = mandates.filter(init_req_flag = True)
		elif status == 'npci':
			subquery = Presentation.objects.exclude(npci_upload_time = None).values("id")
			mandates = mandates.filter(presentation__npci_status = None, presentation__npci_upload_error = None, presentation__id__in=Subquery(subquery))
		elif status == 'error':
			mandates = mandates.exclude(presentation__npci_upload_error = None)

	if 'debit_date' in request.GET.keys() and request.GET['debit_date']:
		mandates = mandates.filter(debit_date = request.GET['debit_date'])
	
	if 'records' in request.GET.keys() and request.GET['records']:
		num_records = request.GET['records']
	else:
		num_records = 10

	if 'pagenum' in request.GET.keys() and request.GET['pagenum']:
		page = request.GET['pagenum']
		print(page)
	else:
		page = 1

	p = Paginator(mandates, num_records)
	context = {"mandates": p.page(pagenum), "range": p.page_range}
	context['form'] = form

	return render(request, "mandate/paginate.html", context)

def paginate_api(request, page):
	mandates = Mandate.objects.exclude(mandate_image__isnull=True).exclude(mandate_image__exact = '')
	p = Paginator(mandates, 30)
	items = serializers.serialize("json", p.page(page), fields=[
		'name_of_debtor_account_holder',
		'debtor_bank',
		'debtor_legal_account_number',
		'umrn',
		'amount'])
	context = {"items": items}
	return JsonResponse(items, safe=False)


def mandate_create(request):
	branch = request.user.userextended.office
	if request.method == 'POST':
		form = MandateForm(branch, request.POST)
		if form.is_valid():
			#save form
			mandate = form.save()
			mandate.create_user = request.user
			mandate.create_time = datetime.now()
			try:
				mandate.seq_no = Mandate.objects.filter(create_time__gte=to_midnight(date.today())).latest("seq_no").seq_no + 1
			except Mandate.DoesNotExist:
				mandate.seq_no = 1
			mandate.set_ref()
			mandate.save()
			return HttpResponseRedirect("/mandates/mandate/" + str(mandate.id) + "/")
	else:
		form = MandateForm(branch)
	return render(request, "mandate/mandate_form.html", {"form": form})


# Prefilled mandate form from another mandate
def mandate_clone(request, id):
	try:
		original_mandate = Mandate.objects.get(id=id)
	except Mandate.DoesNotExist:
		raise Http404
	
	branch = request.user.userextended.office
	if request.method == 'POST':
		form = MandateForm(branch, request.POST)
		if form.is_valid():
			#save form
			mandate = form.save()
			mandate.create_user = request.user
			mandate.create_time = datetime.now()
			try:
				mandate.seq_no = Mandate.objects.filter(create_time__gte=to_midnight(date.today())).latest("seq_no").seq_no + 1
			except Mandate.DoesNotExist:
				mandate.seq_no = 1
			mandate.set_ref()
			mandate.save()
			return HttpResponseRedirect("/mandates/mandate/" + str(mandate.id) + "/")
	else:
		form = MandateForm(branch, instance=original_mandate)
	return render(request, "mandate/mandate_form.html", {"form": form})


def mandate_detail(request, id):
	try:
		mandate = Mandate.objects.get(id=id)
	except Mandate.DoesNotExist:
		raise Http404
	
	if not user_mandate_allowed(request.user, mandate):
		return HttpResponse('Unauthorized request')

	if request.method == 'POST':
		form = MandateImageForm(request.POST, request.FILES, instance=mandate)
		if form.is_valid():
			#save form
			form.save()
			mandate.submit_user = request.user
			mandate.submit_time = datetime.now()

			mandate.last_init_req_time = mandate.submit_time
			mandate.last_init_req_user = mandate.submit_user
			mandate.init_req_flag = True
			
			mandate.save()
			return HttpResponse(MEDIA_URL + mandate.mandate_image.name)
			return HttpResponseRedirect("/mandates/mandate/" + str(mandate.id) + "/")
	else:
		form = MandateImageForm(instance=mandate)

	context = {"mandate": mandate, "form": form}
	
	if mandate.mandate_image:
		presentation = mandate.presentation_set.exclude(npci_upload_time__exact = None)
		context['presentation'] = presentation
	
	return render(request, "mandate/mandate_detail.html", context)


def mandate_print(request, id):
	try:
		mandate = Mandate.objects.get(id=id)
	except Mandate.DoesNotExist:
		raise Http404

	if not user_mandate_allowed(request.user, mandate):
		return HttpResponse('Unauthorized request')
	
	return render(request, "mandate/mandate_print.html", {"mandate": mandate})


def mandate_download(request):
	if request.method == 'POST':
		npci_user = request.POST.get('user')
		if request.POST.getlist('download'):
			file_zip = tempfile.TemporaryFile()
			zip = zipfile.ZipFile(file_zip, 'w')
			zip_object = zip_object_factory(npci_user)
			
			for id in request.POST.getlist('download'):
				m = Mandate.objects.get(id=id)
				print(m.id, m.mandate_image)

				p = presentation_object_factory(npci_user)
				p.mandate = m
				p.zip = zip_object
				p.save()
				
				with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
					fp.write(makeJpg(m.mandate_image).read())
					fp.close()
					zip.write(fp.name, arcname=p.filename_prefix + '_detailfront.jpg')
				
				with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
					fp.write(makeTif(m.mandate_image).read())
					fp.close()
					zip.write(fp.name, arcname=p.filename_prefix + '_front.tif')
				
				with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
					fp.write(makeXml(m, p.npci_MsgId).read())
					fp.close()
					zip.write(fp.name, arcname=p.filename_prefix + '-INP.xml')
			
			zip.close()
			file_zip.seek(0)
			response = HttpResponse(
				call_java_for_crypto("enc", file_zip.read()),
				headers={
					"Content-Type": "application/zip",
					"Content-Disposition": 'attachment; filename="' + zip_object.filename + '"',
				},
			)
			return response

	mandates = Mandate.objects.filter(is_deleted = False, init_req_flag = True, date__lte = date.today()).order_by('id')
	context = {"mandates": mandates}
	return render(request, "mandate/mandate_download.html", context)


def npciAck(request):
	ctx = {}
	if request.method == "POST":
		print('inside request.POST')
		form = NpciAckForm(request.POST, request.FILES)
		if form.is_valid():
			file = request.FILES['file']
			encrypted_bytes = file.read()
			decrypted_file = io.BytesIO(call_java_for_crypto("dec", encrypted_bytes))

			ack_files = zip2dict(decrypted_file)
			status_list = []
			for f in ack_files:
				# file.name is used as fallback mechanism to get presentation
				status_dict = process_ack(f, file.name)
				status_list.append(status_dict)
			ctx['status_list'] = status_list
		
	else:
		form = NpciAckForm()
	
	ctx['form'] = form
	return render(request, "mandate/npci_ack.html", ctx)


def npciStatus(request):
	ctx = {}

	if request.method == "POST":
		print('inside request.POST')
		form = NpciStatusForm(request.POST, request.FILES)
		if form.is_valid():
			messages = process_status(request.FILES['file'])
			ctx['messages'] = messages

	else:
		form = NpciStatusForm()

	ctx['form'] = form	
	return render(request, "mandate/npci_status.html", ctx)


def searchAcc(request):
	base_queryset = get_mandate_queryset(request.user.userextended.office)
	ctx = {}

	try:
		searchKey = request.GET['account']
		if (len(searchKey) < 4):
			resultSet = base_queryset.none()
		else:
			resultSet = base_queryset.filter(
				Q(credit_account__istartswith = searchKey) |
				Q(presentation__npci_umrn__iexact = searchKey) |
				Q(debtor_acc_no__iexact = searchKey) |
				Q(debtor_name__icontains = searchKey) |
				Q(debtor_name_2__icontains = searchKey) |
				Q(debtor_name_3__icontains = searchKey)
			).distinct()
		form = SearchAcc(request.GET)
	except MultiValueDictKeyError:
		form = SearchAcc()

	ctx['form'] = form
	ctx['mandates'] = resultSet
	return render(request, "mandate/search_acc.html", ctx)


def reinit_request(request, id):
	if request.method == "POST":
		mandate = Mandate.objects.get(id=id)
		mandate.init_req_flag = True
		mandate.last_init_req_time = datetime.now()
		mandate.last_init_req_user = request.user
		mandate.save()
		return HttpResponseRedirect("/mandates/mandate/" + str(mandate.id) + "/")


def check_mandate_by_acc_api(request):
	acc = request.GET['account']
	mandates = Mandate.objects.filter(credit_account__exact = acc)
	
	if mandates.count() == 0:
		return HttpResponseNotFound('Not found: ' + acc)
	
	elif mandates.count() >= 0:
		ctx = {'mandates': mandates}
		return render(request, "mandate/include/mandate_table.html", ctx)


def delete_image(request, id):
	try:
		mandate = Mandate.objects.filter(is_deleted=False).get(id=id)
	except Mandate.DoesNotExist:
		raise Http404("Mandate either does not exist or is deleted")
	
	if not user_mandate_allowed(request.user, mandate):
		HttpResponse('Unauthorized', status=401)
	
	if request.method == "POST":
		if mandate.delete_image():
			return HttpResponseRedirect("/mandates/mandate/" + str(mandate.id) + "/")
		else:
			return HttpResponse('Could not delete mandate image.', status=500)


def delete_mandate(request, id):
	try:
		mandate = Mandate.objects.filter(is_deleted=False).get(id=id)
	except Mandate.DoesNotExist:
		raise Http404("Mandate either does not exist or is deleted")
	
	if not user_mandate_allowed(request.user, mandate):
		return HttpResponse('Unauthorized', status=401)
	
	if request.method == "POST":
		if mandate.delete_mandate(request.user):
			return HttpResponse("Deleted")
		else:
			return HttpResponse('Could not delete mandate.', status=500)

@login_not_required
def sop(request):
	return render(request, "mandate/sop.html")


def cancelRequest(request, id):
	try:
		pres = Presentation.objects.get(id=id)
	except Presentation.DoesNotExist:
		raise Http404("Invalid parameter 'id'")
	
	mandate = pres.mandate
	if not user_mandate_allowed(request.user, mandate):
		return HttpResponse('Unauthorized', status=401)
	
	if request.method == 'POST':
		if pres.setCancelReq(request.user):
			return HttpResponse("Cancel Req Flag set to 'True'")
		else:
			return HttpResponse('Bad request', status=401)


def cancelMark(request, id):
	if request.user.userextended.office.type != 'HO':
		return HttpResponse('Unauthorized', status=401)

	try:
		pres = Presentation.objects.get(id=id)
	except Presentation.DoesNotExist:
		raise Http404("Invalid parameter 'id'")
	
	if request.method == 'POST':
		if pres.markCancelled(request.user):
			return HttpResponse("Presentation cancelled")
		else:
			return HttpResponse('Bad request', status=401)