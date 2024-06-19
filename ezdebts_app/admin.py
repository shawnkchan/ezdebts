from django.contrib import admin
from .models import Currencies, UserData, Expenses

# Register your models here.
admin.site.register(UserData)
admin.site.register(Currencies)
admin.site.register(Expenses)