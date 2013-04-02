from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'mainsite.views.index', name='index'),
    url(r'^about/$', 'mainsite.views.about', name='about'),
    url(r'^decks/$', 'mainsite.views.decks', name='decks'),
    url(r'^profile/$', 'mainsite.views.profile', name='profile'),
    url(r'^login/', 'mainsite.views.login_view'),
    url(r'^logout/', 'mainsite.views.logout_view'),
    url(r'^register/', 'mainsite.views.register'),
    url(r'^info/(?P<set_name>\w+)/(?P<card_name>[\w\-\s]+)/$', 'mainsite.views.card_info'),
    url(r'^search/', include('haystack.urls')),
    url(r'^top_decks/', 'mainsite.views.top_decks'),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
