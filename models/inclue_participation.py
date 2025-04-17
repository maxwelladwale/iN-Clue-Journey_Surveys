from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)

class InclueParticipation(models.Model):
    _name = 'inclue.participation'
    _description = 'Tracks user participation in the iN-Clue journey'
    _order = 'create_date desc'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True
    )
    
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Participant',
        required=True,
        help="The partner associated with this participation."
    )
    event_id = fields.Many2one(
        comodel_name='event.event',
        string='Event',
        required=True,
        help="The event associated with this participation."
    )
    survey_id = fields.Many2one(
        comodel_name='survey.survey',
        string='Linked Survey',
        help="The survey associated with this participation."
    )
    user_input_id = fields.Many2one(
        comodel_name='survey.user_input',
        string='Survey Response',
        help="The user's response to the survey."
    )
    survey_sent = fields.Boolean(
        string='Survey Sent',
        default=False,
        help="Indicates if the survey has been sent to the participant."
    )
    session_type = fields.Selection([
        ('kickoff', 'KickOff Session'),
        ('followup1', 'FollowUp Session 1'),
        ('followup2', 'FollowUp Session 2'),
        ('followup3', 'FollowUp Session 3'),
        ('followup4', 'FollowUp Session 4'),
        ('followup5', 'FollowUp Session 5'),
        ('followup6', 'FollowUp Session 6'),
    ], string='Session Type', default='kickoff')
    completed = fields.Boolean(
        string='Completed',
        default=False,
        help="Indicates if the participation has been completed."
    )
    date_completed = fields.Datetime(
        string='Completion Date',
        help="The date when the participation was completed."
    )
    
    # Enhanced fields for tracking journey
    journey_progress = fields.Float(
        string='Journey Progress (%)',
        compute='_compute_journey_progress',
        store=True,
        help="Percentage of the journey completed by this participant"
    )
    
    next_session_date = fields.Date(
        string='Next Session Date',
        help="Scheduled date for the next follow-up session"
    )
    
    next_step_description = fields.Html(
        string='Next Step',
        compute='_compute_next_step',
        help="Description of the next step in the journey"
    )
    
    facilitator_id = fields.Many2one(
        'res.users',
        string='Facilitator',
        related='event_id.user_id',
        store=True,
        help="The user responsible for facilitating this session"
    )
    
    reminder_sent = fields.Boolean(
        string='Reminder Sent',
        default=False,
        help="Whether a reminder has been sent for this survey"
    )
    
    # For portal access
    access_token = fields.Char('Security Token', copy=False)
    
    @api.depends('partner_id.name', 'event_id.name', 'session_type')
    def _compute_name(self):
        for rec in self:
            session_label = dict(self._fields['session_type'].selection).get(rec.session_type, 'Unknown')
            rec.name = f"{rec.partner_id.name or 'Unknown'} - {rec.event_id.name or 'Unknown'} ({session_label})"
    
    @api.depends('session_type', 'completed')
    def _compute_journey_progress(self):
        for rec in self:
            # Define weights for different session types
            weights = {
                'kickoff': 20,
                'followup1': 30, 
                'followup2': 50,
                'followup3': 60,
                'followup4': 70,
                'followup5': 80,
                'followup6': 100,
            }
            if rec.completed:
                rec.journey_progress = weights.get(rec.session_type, 0)
            else:
                # If not completed, progress is the previous step's weight
                current_weight = weights.get(rec.session_type, 0)
                previous_weights = [w for s, w in weights.items() if w < current_weight]
                rec.journey_progress = max(previous_weights) if previous_weights else 0
    
    @api.depends('session_type', 'completed')
    def _compute_next_step(self):
        for rec in self:
            if not rec.completed:
                rec.next_step_description = f"""
                <div class="alert alert-info">
                    <i class="fa fa-info-circle"></i> <strong>Next Step:</strong> Complete the current survey for 
                    {dict(self._fields['session_type'].selection).get(rec.session_type, 'Unknown')}
                </div>
                """
            else:
                # Map current session to next session
                next_session_map = {
                    'kickoff': 'followup1',
                    'followup1': 'followup2',
                    'followup2': 'followup3',
                    'followup3': 'followup4',
                    'followup4': 'followup5',
                    'followup5': 'followup6',
                }
                
                if rec.session_type in next_session_map:
                    next_session = next_session_map[rec.session_type]
                    next_session_label = dict(self._fields['session_type'].selection).get(next_session, 'Unknown')
                    
                    rec.next_step_description = f"""
                    <div class="alert alert-success">
                        <i class="fa fa-check-circle"></i> <strong>Current session completed!</strong>
                        <p>Your next step is to attend the {next_session_label}</p>
                    </div>
                    """
                else:
                    rec.next_step_description = """
                    <div class="alert alert-success">
                        <i class="fa fa-trophy"></i> <strong>Congratulations!</strong>
                        <p>You have completed the entire iN-Clue Journey! Thank you for your participation.</p>
                    </div>
                    """
    
    @api.model
    def create(self, vals):
        _logger.info("Creating a new inclue.participation record with vals: %s", vals)
        participation = super(InclueParticipation, self).create(vals)
        _logger.info("Created inclue.participation record with ID: %s", participation.id)
        
        # Generate access token for portal access
        participation._portal_ensure_token()
        
        if participation.survey_id and not participation.survey_sent:
            _logger.info("Survey is linked and not sent yet. Attempting to send email for participation ID: %s", participation.id)
            participation.send_survey_email()
        return participation

    def send_survey_email(self):
        _logger.info("send_survey_email() called for participation ID: %s", self.id)

        # Get the template
        template = self.env.ref('inclueyoh.mail_template_inclue_survey', raise_if_not_found=False)
        if not template:
            _logger.error("❌ Survey email template not found for participation ID: %s. Skipping survey sending.", self.id)
            return False

        try:
            # Generate the user input if not yet generated
            if not self.user_input_id:
                user_input = self.env['survey.user_input'].create({
                    'survey_id': self.survey_id.id,
                    'partner_id': self.partner_id.id,
                })
                self.user_input_id = user_input.id
                _logger.info("Survey user_input created with ID %s", user_input.id)
            else:
                user_input = self.user_input_id
            
            # Check if the user_input has a token
            if not user_input.token:
                _logger.error("❌ No token found for user_input ID: %s. Skipping survey email sending.", user_input.id)
                return False

            # Send email using the template
            mail_id = template.send_mail(self.id, force_send=False)  # force_send=False = queued
            mail = self.env['mail.mail'].browse(mail_id)

            _logger.info(
                "📨 Mail %s created from template ID %s for %s. State=%s, From=%s, To=%s",
                mail_id, template.id, self.partner_id.email, mail.state, mail.email_from, mail.email_to
            )

            # Send it manually and catch any SMTP-level issues
            mail.send(raise_exception=True)

            # Mark as sent
            self.survey_sent = True
            _logger.info("✅ Survey email successfully sent to %s (Mail ID: %s)", self.partner_id.email, mail_id)
            return True

        except Exception as e:
            _logger.exception("❌ Failed to send survey email to %s for participation ID: %s. Exception: %s", self.partner_id.email, self.id, e)
            return False
    
    def send_reminder_email(self):
        """Send a reminder email for incomplete surveys"""
        self.ensure_one()
        
        if self.completed or not self.survey_sent or self.reminder_sent:
            return False
        
        # Get the template - you'll need to create this template
        template = self.env.ref('inclueyoh.mail_template_inclue_survey_reminder', raise_if_not_found=False)
        if not template:
            _logger.error("❌ Survey reminder template not found for participation ID: %s", self.id)
            return False

        try:
            # Send email using the template
            mail_id = template.send_mail(self.id, force_send=True)
            self.reminder_sent = True
            _logger.info("✅ Survey reminder email sent to %s (Mail ID: %s)", self.partner_id.email, mail_id)
            return True
        except Exception as e:
            _logger.exception("❌ Failed to send reminder: %s", e)
            return False
    
    def schedule_next_session(self):
        """Schedule the next follow-up session for this participant"""
        self.ensure_one()
        
        if not self.completed:
            _logger.warning("Cannot schedule next session for incomplete participation ID: %s", self.id)
            return False
            
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
            _logger.info("This is the final session. No next session to schedule for participation ID: %s", self.id)
            return False
            
        next_session_type = next_session_map[self.session_type]
        next_session_date = fields.Date.today() + timedelta(days=30)  # Schedule 30 days later by default
        
        # Find if a next session event already exists
        next_event = self.env['event.event'].search([
            ('session_type', '=', next_session_type),
            ('date_begin', '>=', fields.Datetime.now()),
            ('state', '=', 'confirm')
        ], limit=1)
        
        if not next_event:
            _logger.warning("No upcoming event found for session type %s", next_session_type)
            return False
            
        # Check if participation already exists
        existing_participation = self.search([
            ('partner_id', '=', self.partner_id.id),
            ('event_id', '=', next_event.id),
            ('session_type', '=', next_session_type)
        ], limit=1)
        
        if existing_participation:
            _logger.info("Participation already exists for next session. ID: %s", existing_participation.id)
            return existing_participation
            
        # Create next participation record
        next_participation = self.create({
            'partner_id': self.partner_id.id,
            'event_id': next_event.id,
            'survey_id': next_event.survey_id.id,
            'session_type': next_session_type,
            'next_session_date': next_session_date
        })
        
        _logger.info("Created next participation record with ID: %s", next_participation.id)
        return next_participation
    
    @api.model
    def process_survey_completion(self, survey_user_input):
        """Called when a survey is completed to update participation records"""
        participation = self.search([
            ('user_input_id', '=', survey_user_input.id)
        ], limit=1)
        
        if participation:
            participation.write({
                'completed': True,
                'date_completed': fields.Datetime.now()
            })
            
            # Check if we should schedule next session
            if participation.session_type != 'followup6':  # Not the final session
                participation.schedule_next_session()
                
            return participation
        return False