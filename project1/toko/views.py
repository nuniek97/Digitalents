from django.template import loader
from django.http import HttpResponse
from .models import Toko

# Create your views here.
def toko(request):
    tokoku = Toko.objects.all().values()
    template = loader.get_template('all_toko.html')

    context = {
        'tokoku': tokoku,
    }
    return HttpResponse(template.render(context, request))
