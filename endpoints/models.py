from django.db import models


class Contact(models.Model):
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)
    email = models.EmailField()

    def __unicode__(self):
        return "Contact: %s %s (%s)".format(
            self.first_name, self.last_name, self.email)


class Defect(models.Model):
    description = models.CharField(max_length=256)

    def __unicode__(self):
        return self.description


class Product(models.Model):
    name = models.CharField(max_length=256)
    contacts = models.ManyToManyField(Contact)

    def __unicode__(self):
        return "Product: %s" % (self.name)


class TestResult(models.Model):
    time = models.DateTimeField()
    ip_address = models.CharField(max_length=256)
    score = models.CharField(max_length=16)
    defects = models.ManyToManyField(Defect)
    the_endpoint = models.ForeignKey("Endpoint")

    def __unicode__(self):
        return "Test Result: Score(%s);Time(%s)" % (self.score, self.time)


class Endpoint(models.Model):
    url = models.URLField()
    test_results = models.ManyToManyField(TestResult)
    product = models.ForeignKey(Product)
    expiry_date = models.DateField(null=True, default=None)

    def __unicode__(self):
        return "Endpoint: %s" % (self.url)


class Setting(models.Model):
    default_email = models.EmailField(default='security.engineering@rackspace.com')
    scan_enabled = models.BooleanField(default=False)
    default_scan_frequency = models.IntegerField(default=1)
    scan_score_threshold = models.CharField(max_length=16)
    auto_purge = models.BooleanField(default=False)
    test_retention_period = models.IntegerField(default=1)
