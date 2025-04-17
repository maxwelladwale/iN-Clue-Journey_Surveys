from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class EventEvent(models.Model):
    _inherit = 'event.event'

    survey_id = fields.Many2one(
        comodel_name='survey.survey',
        string='Survey',
        help="Survey to be sent to attendees after the event."
    )
    survey_sent = fields.Boolean(
        string='Survey Sent',
        default=False,
        help="Indicates if the survey has been sent to attendees."
    )
    
    session_type = fields.Selection([
        ('kickoff', 'KickOff Session'),
        ('followup1', 'FollowUp Session 1'),
        ('followup2', 'FollowUp Session 2'),
        ('followup3', 'FollowUp Session 3'),
        ('followup4', 'FollowUp Session 4'),
        ('followup5', 'FollowUp Session 5'),
        ('followup6', 'FollowUp Session 6'),
    ], string='Session Type', default='kickoff',
    help="Specify what type of session this event represents in the iN-Clue journey")
    
    participation_ids = fields.One2many(
        'inclue.participation', 
        'event_id', 
        string='Participations'
    )
    
    total_participants = fields.Integer(
        string='Total Participants',
        compute='_compute_participation_stats',
        store=True
    )
    
    completed_surveys = fields.Integer(
        string='Completed Surveys',
        compute='_compute_participation_stats',
        store=True
    )
    
    completion_rate = fields.Float(
        string='Completion Rate (%)',
        compute='_compute_participation_stats',
        store=True
    )
    
    @api.depends('participation_ids', 'participation_ids.completed')
    def _compute_participation_stats(self):
        for event in self:
            total = len(event.participation_ids)
            completed = len(event.participation_ids.filtered(lambda p: p.completed))
            
            event.total_participants = total
            event.completed_surveys = completed
            event.completion_rate = (completed / total * 100) if total > 0 else 0.0

    def action_send_inclue_survey(self):
        _logger.info("action_send_inclue_survey() called for event IDs: %s", self.ids)
        participation_model = self.env['inclue.participation']

        for event in self:
            _logger.info("Processing Event ID: %s", event.id)

            # Skip if survey already sent
            if event.survey_sent:
                _logger.info("Survey already sent for event ID %s. Skipping.", event.id)
                event.message_post(body="ℹ️ Surveys have already been sent for this event. Skipping.")
                continue

            if not event.survey_id:
                _logger.warning("No survey linked to event ID: %s. Skipping survey sending.", event.id)
                event.message_post(body="⚠️ No survey linked to event. Skipping survey sending.")
                continue

            emails_sent = 0
            emails_failed = 0

            for registration in event.registration_ids.filtered(lambda r: r.state == 'done'):
                partner = registration.partner_id
                if not partner or not partner.email:
                    _logger.warning("Skipping registration ID %s: Missing partner or email.", registration.id)
                    continue

                _logger.info("Processing registration ID: %s for partner: %s", registration.id, partner.name)

                participation = participation_model.search([
                    ('event_id', '=', event.id),
                    ('partner_id', '=', partner.id),
                    ('survey_id', '=', event.survey_id.id),
                ], limit=1)

                if participation:
                    if participation.survey_sent:
                        _logger.info("Survey already sent to partner: %s. Skipping.", partner.name)
                        continue
                    _logger.info("Existing participation record found with ID: %s for partner: %s", participation.id, partner.name)
                else:
                    _logger.info("No participation record found. Creating one for partner: %s", partner.name)
                    participation = participation_model.create({
                        'event_id': event.id,
                        'partner_id': partner.id,
                        'survey_id': event.survey_id.id,
                        'session_type': event.session_type or 'kickoff',
                        'survey_sent': False,
                    })
                    _logger.info("Created new participation record with ID: %s", participation.id)

                if participation.send_survey_email():
                    participation.survey_sent = True
                    emails_sent += 1
                else:
                    emails_failed += 1

            _logger.info("For event ID %s, emails sent: %s, emails failed: %s", event.id, emails_sent, emails_failed)

            if emails_sent:
                event.survey_sent = True
                event.message_post(body=f"✅ Survey sent to {emails_sent} attendee(s).")
            if emails_failed:
                event.message_post(body=f"⚠️ Failed to send survey to {emails_failed} attendee(s).")
                
    def action_schedule_next_session(self):
        """Schedule the next follow-up session for this event's participants"""
        self.ensure_one()
        
        # Map current session to next session
        next_session_map = {
            'kickoff': 'followup1',
            'followup1': 'followup2',
            'followup2': 'followup3',
            'followup3': 'followup4',
            'followup4': 'followup5',
            'followup5': 'followup6',
        }
        
        if self.session_type not in next_session_map:
            self.message_post(body="⚠️ This is the final session type. Cannot schedule next session.")
            return
            
        next_session_type = next_session_map[self.session_type]
        
        # Create a new event for the next session
        next_event = self.copy({
            'name': f"{self.name} - {dict(self._fields['session_type'].selection).get(next_session_type)}",
            'date_begin': fields.Datetime.now() + fields.Datetime.to_timedelta("7 days"),
            'date_end': fields.Datetime.now() + fields.Datetime.to_timedelta("7 days 3 hours"),
            'session_type': next_session_type,
            'survey_sent': False
        })
        
        self.message_post(body=f"✅ Next session '{next_event.name}' scheduled successfully.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.event',
            'res_id': next_event.id,
            'view_mode': 'form',
            'target': 'current',
        }