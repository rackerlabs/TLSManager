from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView
from django.contrib import admin
from .views import start_periodic_reporting, kickoff_periodic_scans

admin.autodiscover()

urlpatterns = patterns(
    "",
    url(r'^admin/', include(admin.site.urls)),
    url(r"^$", "endpoints.views.list_test_results"),
    url(r"^dashboard/$", "endpoints.views.list_test_results"),
    url(r"^dashboard/(?P<page2return2>\d{1,2})/$", "endpoints.views.list_test_results"),
    url(r"^testDetails/(?P<result_id>\d{1,11})/(?P<page2return2>\d{1,2})/$", "endpoints.views.test_result_details"),
    url(r"^deleteTestResultDetails$", "endpoints.views.delete_test_result_details"),
    url(r"^settings$", "endpoints.views.configure"),
    url(r"^addURL$", "endpoints.views.add_url"),
    # --- change URL details ---
    #url(r"^getChangeURLDetails$", "endpoints.views.get_change_url_details"),
    url(r"^changeURLDetails$", "endpoints.views.change_url_details"),
    url(r"^deleteURLDetails$", "endpoints.views.delete_url_details"),
    url(r"^searchURL/?$", "endpoints.views.search_url"),
    url(r"^summaryReport$", "endpoints.views.summary_report"),
    url(r"^certReport$", "endpoints.views.cert_report"),
    # --- contact ---
    url(r"^addContact/?$", "endpoints.views.add_contact"),
    url(r"^getChangeContact$", "endpoints.views.get_change_contact"),
    url(r"^changeContact/?$", "endpoints.views.change_contact"),
    url(r"^updateContact/?$", "endpoints.views.update_contact"),
    url(r"^searchContact/?$", "endpoints.views.search_contact"),
    url(r"^deleteContact/?$", "endpoints.views.delete_contact"),
    # --- product ---
    url(r"^searchProduct/?$", "endpoints.views.search_product"),
    url(r"^addProduct$", "endpoints.views.add_product"),
    url(r"^changeProduct$", "endpoints.views.change_product"),
    url(r"^updateProduct$", "endpoints.views.update_product"),
    url(r"^productSummary$", "endpoints.views.product_overview"),
    url(r"^product/(?P<product_id>[0-9]+)/$", "endpoints.views.product_results"),
    # --- misc ---
    #url(r"^deleteURL/?$", "endpoints.views.delete_url"),
    url(r"^submitForScan$", "endpoints.views.submit_for_scan"),
    #url(r"^purgeOldTests$", "endpoints.views.purge_old_tests"),
    #url(r"^sendEmailToContact/?$", "endpoints.views.send_email_to_contact"),
    # --- login ---
    url(r'^login$', 'django.contrib.auth.views.login',
        {'template_name': 'login.html'}, name='login'),
    url(r"^logout/?$", "endpoints.views.logout"),
    url(r"^init/?$", "endpoints.views.init_threads"),
)


