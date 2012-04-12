# coding: utf-8
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _, ugettext_noop
from django.utils import simplejson
from modoboa.lib.webutils import _render, _render_to_string, ajax_simple_response
from modoboa.lib.permissions import check_domain_access
from modoboa.admin.models import Domain, Mailbox
from django.contrib.auth.decorators \
    import login_required, user_passes_test, permission_required
from modoboa.extensions.stats.grapher import *
from modoboa.lib.exceptions import *

graph_types = ['AVERAGE', 'MAX']
graph_list = [{"name" : "traffic", "label" : ugettext_noop("Average normal traffic")},
              {"name" : "badtraffic", "label" : ugettext_noop("Average bad traffic")},
              {"name" : "size", "label" : ugettext_noop("Average normal traffic size")}]
periods = [{"name" : "day", "label" : ugettext_noop("Day")},
           {"name" : "week", "label" : ugettext_noop("Week")},
           {"name" : "month", "label" : ugettext_noop("Month")},
           {"name" : "year", "label" : ugettext_noop("Year")},
           {"name" : "custom", "label" : ugettext_noop("Custom")}]

@login_required
@permission_required("admin.view_mailboxes")
@check_domain_access
def index(request):
    domains = None
    period = request.GET.get("period", "day")
    domid = request.GET.get("domid", "")

    domains = request.user.get_domains()

    return _render(request, 'stats/index.html', {
            "domains" : domains,
            "graphs" : graph_list,
            "periods" : periods,
            "period" : period,
            "selection" : "stats",
            "domid" : domid
            })

@login_required
@user_passes_test(lambda u: u.group != "SimpleUsers")
def graphs(request):
    view = request.GET.get("view", None)
    if not view:
        raise ModoboaException(_("Invalid request"))
    period = request.GET.get("period", "day")
    tplvars = dict(graphs=graph_list, period=period)
    if view == "global":
        if not request.user.is_superuser:
            raise PermDeniedError(_("you're not allowed to see those statistics"))
        tplvars.update(domain=view)
    else:
        try:
            domain = Domain.objects.get(name=view)
        except Domain.DoesNotExist:
            raise ModoboaException(_("Domain not found. Please enter a full name"))
        if not request.user.can_access(domain):
            raise PermDeniedError(_("You don't have access to this domain"))
        tplvars.update(domain=domain.name)

    if period == "custom":
        if not request.GET.has_key("start") or not request.GET.has_key("end"):
            raise ModoboaException(_("Bad custom period"))
        start = request.GET["start"]
        end = request.GET["end"]
        G = Grapher()
        period_name = "%s_%s" % (start.replace('-',''), end.replace('-',''))
        for tpl_name in graph_list:
            G.process(tplvars["domain"],
                      period_name,
                      str2Time(*start.split('-')),
                      str2Time(*end.split('-')),
                      tpl[tpl_name['name']])
        tplvars["period_name"] = period_name
        tplvars["start"] = start
        tplvars["end"] = end

    return ajax_simple_response(dict(
            status="ok", content=_render_to_string(request, "stats/graphs.html", tplvars)
            ))
