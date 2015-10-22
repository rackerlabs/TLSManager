from django.contrib import admin
from endpoints.models import Contact, Defect, Product, TestResult, Endpoint
# Register your models here.

admin.site.register(Contact)
admin.site.register(Defect)
admin.site.register(Product)
admin.site.register(TestResult)
admin.site.register(Endpoint)
