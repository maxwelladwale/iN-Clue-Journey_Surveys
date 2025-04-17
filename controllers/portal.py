from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv.expression import OR
from odoo.exceptions import AccessError, MissingError
import logging

_logger = logging.getLogger(__name__)

class IncluePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        
        if 'participation_count' in counters:
            participation_count = request.env['inclue.participation'].search_count([
                ('partner_id', '=', request.env.user.partner_id.id)
            ])
            values['participation_count'] = participation_count
            
        return values
        
    def _get_inclue_participation_domain(self, search_in, search):
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        
        if search and search_in:
            search_domain = []
            if search_in in ('all', 'event'):
                search_domain = OR([search_domain, [('event_id.name', 'ilike', search)]])
            if search_in in ('all', 'session_type'):
                search_domain = OR([search_domain, [('session_type', 'ilike', search)]])
            domain += search_domain
            
        return domain
        
    def _get_inclue_participation_searchbar_inputs(self):
        return {
            'all': {'input': 'all', 'label': _('Search in All')},
            'event': {'input': 'event', 'label': _('Search in Events')},
            'session_type': {'input': 'session_type', 'label': _('Search in Session Types')},
        }
        
    def _get_inclue_participation_searchbar_sortings(self):
        return {
            'date': {'label': _('Event Date'), 'order': 'event_id.date_begin desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'session_type': {'label': _('Session Type'), 'order': 'session_type'},
            'progress': {'label': _('Progress'), 'order': 'journey_progress desc'},
        }
        
    def _get_inclue_participation_searchbar_groupby(self):
        return {
            'none': {'input': 'none', 'label': _('None')},
            'event': {'input': 'event', 'label': _('Event')},
            'session_type': {'input': 'session_type', 'label': _('Session Type')},
        }
        
    @http.route(['/my/inclue', '/my/inclue/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_inclue(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        Participation = request.env['inclue.participation']
        
        # Default sort by event date
        if not sortby:
            sortby = 'date'
        sort_order = self._get_inclue_participation_searchbar_sortings()[sortby]['order']
        
        # Search
        searchbar_sortings = self._get_inclue_participation_searchbar_sortings()
        searchbar_inputs = self._get_inclue_participation_searchbar_inputs()
        searchbar_groupby = self._get_inclue_participation_searchbar_groupby()
        
        # Search domain
        domain = self._get_inclue_participation_domain(search_in, search)
        
        # Count for pager
        participation_count = Participation.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/inclue",
            url_args={'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=participation_count,
            page=page,
            step=self._items_per_page
        )
        
        # Content
        if groupby == 'event':
            order = "event_id, %s" % sort_order
        elif groupby == 'session_type':
            order = "session_type, %s" % sort_order
        else:
            order = sort_order
            
        participations = Participation.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        
        if groupby == 'event':
            grouped_participations = [Participation.concat(*g) for k, g in participations.grouped_by('event_id')]
        elif groupby == 'session_type':
            grouped_participations = [Participation.concat(*g) for k, g in participations.grouped_by('session_type')]
        else:
            grouped_participations = [participations]
            
        # Calculate overall progress
        all_participations = Participation.search([('partner_id', '=', request.env.user.partner_id.id)])
        if all_participations:
            max_progress = max(all_participations.mapped('journey_progress')) if all_participations else 0
            overall_progress = round(max_progress)
        else:
            overall_progress = 0
            
        values.update({
            'participations': participations,
            'grouped_participations': grouped_participations,
            'page_name': 'inclue',
            'pager': pager,
            'default_url': '/my/inclue',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
            'groupby': groupby,
            'overall_progress': overall_progress,
        })
        
        return request.render("inclueyoh.portal_my_inclue", values)
        
    @http.route(['/my/inclue/<int:participation_id>'], type='http', auth="user", website=True)
    def portal_my_inclue_participation(self, participation_id=None, **kw):
        try:
            participation_sudo = self._document_check_access('inclue.participation', participation_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        values = self._prepare_portal_layout_values()
        values.update({
            'participation': participation_sudo,
            'page_name': 'inclue_participation',
        })
        
        return request.render("inclueyoh.portal_my_inclue_participation", values)