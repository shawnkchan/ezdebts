from django.db import models

# Create your models here.
class UserData(models.Model):
    id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100,blank=True)
    username = models.CharField(max_length=100)
    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} is known as {self.username}"

class Currencies(models.Model):
    USD = "USD"
    SGD = "SGD"
    GBP = "GBP"
    currency_options = {
        (USD, "US Dollar"),
        (SGD, "Singapore Dollar"),
        (GBP, "British Pound"),
    }

    code = models.CharField(max_length=3, choices=currency_options, unique=True)
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=5, unique=True)
    
    def __str__(self) -> str:
        return f"{self.code}, {self.name}, {self.symbol}"

class Expenses(models.Model):
    lender = models.ForeignKey(UserData, on_delete=models.CASCADE, related_name="receivables")
    debtor = models.ForeignKey(UserData, on_delete=models.CASCADE, related_name="debts")
    quantity = models.DecimalField(max_digits=100, decimal_places=2)
    currency = models.ForeignKey(Currencies, on_delete=models.PROTECT, related_name="expenses")

    def __str__(self) -> str:
        return f"lender: {self.lender}, debtor: {self.debtor}, quantity: {self.quantity}, currency: {self.currency}"