#!/usr/bin/env python3
"""
Email Parser for Google Takeout
Parses MBOX files from Google Takeout and counts internship applications.
"""

import mailbox
import os
import re
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime
import email.utils
import email.header


class InternshipApplicationCounter:
    """Counts internship applications from email data."""
    
    # Keywords that suggest an internship application
    APPLICATION_KEYWORDS = [
        'internship',
        'intern',
        'application',
        'applied',
        'apply',
        'position',
        'role',
        'opportunity',
        'candidate',
        'resume',
        'cv',
        'cover letter',
        'hiring',
        'recruiter',
        'interview',
        'job',
        'software engineer',
        'engineering',
        'developer',
        'programming',
        'software',
        'tech',
        'technology',
        'summer',
        'co-op',
        'coop',
    ]
    
    # Keywords that suggest it's NOT an application (rejections, confirmations, etc.)
    EXCLUSION_KEYWORDS = [
        'rejection',
        'declined',
        'not selected',
        'unfortunately',
        'thank you for your interest',
        'thank you for applying',
        'thanks for applying',
        'we have decided',
        'we regret',
        'position has been filled',
        'no longer',
        'job alert',
        'new matches',
        'want to hire you',
        'your job alert',
        'new job',
        'job opportunities',
        'rate the support',
        'welcome to',
        'received your',
        'we\'ve received',
        'application received',
        'confirming your application',
        'application confirmation',
        'thank you =',
    ]
    
    def __init__(self, mbox_path: str):
        """
        Initialize the counter with an MBOX file path.
        
        Args:
            mbox_path: Path to the MBOX file or directory containing MBOX files
        """
        self.mbox_path = Path(mbox_path)
        self.applications: List[Dict] = []
        self.unique_companies: Set[str] = set()
        
    def _is_application_email(self, message) -> bool:
        """
        Determine if an email is likely an internship application.
        
        Args:
            message: Email message object
            
        Returns:
            True if email appears to be an application
        """
        # Get subject and body
        subject = message.get('Subject', '') or ''
        body = self._get_email_body(message)
        
        # Decode subject if it's encoded (common in email headers)
        try:
            decoded_subject = email.header.decode_header(subject)
            subject = ''.join([str(text, encoding or 'utf-8', errors='ignore') 
                             if isinstance(text, bytes) else text 
                             for text, encoding in decoded_subject])
        except:
            pass
        
        # Combine subject and body for analysis
        text = f"{subject} {body}".lower()
        
        # Quick subject-based exclusions (very common non-application patterns)
        subject_lower = subject.lower()
        if any(pattern in subject_lower for pattern in [
            'zelle',
            'payment',
            'gift card',
            'connection request',
            'connect with',
            'want to connect',
            'someone you may',
            'add ',
            'thanks for being',
            'document has been',
            'fafsa',
            'emergency need',
            'blood',
            'statement is available',
            'cash rewards',
            'redemption',
            'choice category',
            'fish texas',
            # College/university application exclusions
            'admission',
            'admissions',
            'enrollment',
            'acceptance',
            'offer',
            'spring entry',
            'fall entry',
            'you\'re invited',
            'your offer',
            'fishing resource',
            'transcript',
        ]):
            return False
        
        # Check for exclusion keywords first (these take priority)
        for exclusion in self.EXCLUSION_KEYWORDS:
            if exclusion.lower() in text:
                return False
        
        # Check if it contains application-related keywords
        keyword_count = sum(1 for keyword in self.APPLICATION_KEYWORDS 
                           if keyword.lower() in text)
        
        # Check if it's a sent email (user sent it, likely an application)
        from_field = message.get('From', '').lower()
        to_field = message.get('To', '').lower()
        labels = message.get('X-Gmail-Labels', '').lower()
        
        # More accurate sent email detection
        # Check multiple indicators that this is a sent email
        is_sent = (
            'sent' in labels or
            'hasenbein' in from_field or
            (from_field.endswith('@gmail.com') and 'hasenbein' in from_field) or
            'me' in from_field or
            # If From contains your email and To is a company email, it's likely sent
            ('hasenbein' in from_field or 'alex' in from_field) and 
            to_field and '@' in to_field and not to_field.endswith('@gmail.com')
        )
        
        # Additional exclusions for common non-application patterns
        if any(pattern in text for pattern in [
            'indeed application:',  # Indeed notifications
            'loopcv',
            'jooble',
            'catch-all',
            'cloudflare',
            'teacher retirement',
            'zelle',
            'payment',
            'gift card',
            'blood',
            'donation',
            'fafsa',
            'student aid',
            'document has been',
            'connection request',
            'add ',
            'thanks for being',
            'valued member',
            'emergency need',
            'statement is available',
            'credit card',
            'bonus reward',
            'enrollment in',
            'paperless settings',
            'delivery status',
            'important information',
            'pro resumes',
            'what it takes',
            'financial planning',
            # College/university application exclusions
            'college application',
            'university application',
            'admission',
            'admissions',
            'enrollment',
            'acceptance',
            'offer of admission',
            'spring entry',
            'fall entry',
            'you\'re invited to learn',
            'your offer',
            'fishing resource',
            'naviance',
            'parchment',
            'transcript',
            'college board',
            'giant leap in medicine',
            'would like your feedback',
            'reminder:',
            'final reminder',
            'radiant',
            # Financial advisor/marketing
            'what can the right advisor',
            'financial strategy',
            'financial plan',
            'merrill',
            'ask merrill',
            # LinkedIn notifications
            'still waiting for your response',
            'on a roll on linkedin',
            'i\'m still waiting',
            # General marketing
            'what\'s new in',
            'your interview',  # TopResume marketing
            # Customer service / support issues
            ' issue',  # matches "issue" or "issue with" or "glove issue"
            'changing form',
            'mistakenly selected',
            'crank pulley',
            'supercharger',
            'hardware for',
            'specs of',
            'glove issue',
        ]):
            return False
        
        # Heuristics - focus on emails YOU sent (applications)
        # Only count received emails if they're very clearly applications
        has_internship = 'intern' in text or 'internship' in text
        has_application = 'applied' in text or 'application' in text
        
        # Check sender domain for common non-application services
        # Extract domain from email
        email_field = from_field if not is_sent else to_field
        domain_match = re.search(r'@([\w\.-]+)', email_field)
        if domain_match:
            domain = domain_match.group(1).lower()
            # Exclude common non-application domains unless they mention internship
            non_app_domains = [
                'bankofamerica.com',
                'bofa.com',
                'topresume.com',
                'indeed.com',
                'linkedin.com',
                'jooble.com',
                'loopcv.com',
            ]
            # Exclude all .edu domains (universities/colleges) unless they mention internship
            if domain.endswith('.edu') and not has_internship:
                return False
            
            # Exclude specific university domains that appeared in results
            university_domains = [
                'nd.edu',  # Notre Dame
                'rutgers.edu',
                'cmu.edu',  # Carnegie Mellon
                'mercer.edu',
                'brown.edu',
                'columbia.edu',
                'northeastern.edu',
                'northwestern.edu',
                'purdue.edu',
                'tamu.edu',  # Texas A&M
                'umich.edu',  # University of Michigan
                'uchicago.edu',
                'smu.edu',  # Southern Methodist University
                'utdallas.edu',
                'unlv.edu',
                'uky.edu',  # University of Kentucky
                'ou.edu',  # University of Oklahoma
                'lamar.edu',
                'carleton.edu',
                'drake.edu',
                'trinity.edu',
                'xavier.edu',
                'lmu.edu',  # Loyola Marymount
                'rwu.edu',  # Roger Williams
                'stonybrook.edu',
                'oregonstate.edu',
                'purdue.edu',
            ]
            if domain in university_domains and not has_internship:
                return False
            
            # Exclude other college-related services
            college_services = [
                'naviance.com',
                'parchment.com',
                'qemailserver.com',
            ]
            if domain in college_services and not has_internship:
                return False
            
            # Exclude marketing/notification services unless they mention internship
            # But only for received emails, not sent emails
            marketing_services = [
                'topresume.com',
                'linkedin.com',
            ]
            if domain in marketing_services and not has_internship and not is_sent:
                return False
            
            if domain in non_app_domains and not has_internship:
                return False
        
        # Primary: Sent emails with internship/application keywords
        # For sent emails, be very lenient - if you sent it to a company, it's likely an application
        if is_sent:
            # Check if it's being sent to a company domain (not .edu, not personal email)
            email_field = to_field if is_sent else from_field
            domain_match = re.search(r'@([\w\.-]+)', email_field)
            is_to_company = False
            if domain_match:
                domain = domain_match.group(1).lower()
                # It's a company if it's not .edu, not common email providers, not college services
                if (not domain.endswith('.edu') and 
                    domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com'] and
                    domain not in ['naviance.com', 'parchment.com', 'qemailserver.com']):
                    is_to_company = True
            
            # If sent to a company domain, be very lenient
            # Assume any email sent to a company is likely an application
            if is_to_company:
                # If it mentions internship, definitely count it
                if has_internship:
                    return True
                # If it has "application" or "applied" keywords, count it
                if has_application:
                    return True
                # If it has any job-related keywords, count it
                if keyword_count >= 1:
                    return True
                # Even without explicit keywords, if sent to company domain, 
                # it's likely an application (but exclude obvious non-app emails via subject checks above)
                # We'll rely on the subject/body exclusions to filter out non-applications
                return True
            
            # For other sent emails (not to company domains), require more keywords
            if has_internship:
                return True
            if has_application:
                return True
            if keyword_count >= 2:
                return True
        
        # Secondary: Received emails that are clearly applications (very strict)
        # Only if it's from a company domain and has strong application signals
        if not is_sent:
            # Must have both internship and application keywords
            if has_internship and has_application:
                # Check if it's from a company (not personal email)
                to_field = message.get('To', '').lower()
                if 'hasenbein' in to_field or '@gmail.com' in to_field:
                    # Likely a confirmation, exclude unless very specific
                    if 'submitted' in text or 'submitted your' in text:
                        return True
        
        return False
    
    def _get_email_body(self, message) -> str:
        """Extract the body text from an email message."""
        body = ""
        
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                payload = message.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            except:
                pass
        
        return body
    
    def _extract_company_name(self, message) -> str:
        """Extract company name from email (To field for sent emails, From for received)."""
        to_field = message.get('To', '')
        from_field = message.get('From', '')
        labels = message.get('X-Gmail-Labels', '').lower()
        
        # Determine if this is a sent email
        is_sent = 'sent' in labels or 'hasenbein' in from_field.lower()
        
        # For sent emails, check the To field; for received, check From field
        email_address = to_field if is_sent else from_field
        
        # Extract email from field (format: "Name <email@domain.com>")
        email_match = re.search(r'[\w\.-]+@([\w\.-]+\.\w+)', email_address)
        if email_match:
            domain = email_match.group(1).lower()
            # Remove common email providers and personal domains
            if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
                            'icloud.com', 'me.com', 'mac.com']:
                # Extract company name from domain (remove common TLDs)
                domain_parts = domain.split('.')
                # Get the main domain part (usually second-to-last)
                if len(domain_parts) >= 2:
                    company = domain_parts[-2]  # e.g., "google" from "careers.google.com"
                    # Clean up common prefixes
                    company = company.replace('careers', '').replace('jobs', '').replace('recruiting', '')
                    if company:
                        return company.title()
        
        # Try to extract from subject line (common patterns)
        subject = message.get('Subject', '')
        # Look for company names in subject (e.g., "Application to Google")
        subject_match = re.search(r'(?:to|at|for)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|:)', subject, re.IGNORECASE)
        if subject_match:
            company = subject_match.group(1).strip()
            if len(company) > 2 and len(company) < 50:
                return company
        
        return "Unknown Company"
    
    def parse_mbox_file(self, mbox_file: Path) -> None:
        """Parse a single MBOX file and extract applications."""
        print(f"Parsing {mbox_file.name}...")
        
        try:
            mbox = mailbox.mbox(str(mbox_file))
            count = 0
            
            for message in mbox:
                if self._is_application_email(message):
                    # Extract email details
                    subject = message.get('Subject', 'No Subject')
                    date = message.get('Date', '')
                    company = self._extract_company_name(message)
                    
                    # Parse date
                    try:
                        parsed_date = email.utils.parsedate_to_datetime(date)
                        date_str = parsed_date.strftime('%Y-%m-%d') if parsed_date else date
                    except:
                        date_str = date
                    
                    application = {
                        'subject': subject,
                        'date': date_str,
                        'company': company,
                        'from': message.get('From', ''),
                        'to': message.get('To', ''),
                    }
                    
                    self.applications.append(application)
                    self.unique_companies.add(company)
                    count += 1
            
            print(f"  Found {count} applications in {mbox_file.name}")
            mbox.close()
            
        except Exception as e:
            print(f"Error parsing {mbox_file}: {e}")
    
    def parse(self) -> None:
        """Parse all MBOX files in the specified path."""
        if self.mbox_path.is_file():
            # Single MBOX file
            self.parse_mbox_file(self.mbox_path)
        elif self.mbox_path.is_dir():
            # Directory - find all MBOX files
            mbox_files = list(self.mbox_path.glob('*.mbox'))
            if not mbox_files:
                print(f"No MBOX files found in {self.mbox_path}")
                return
            
            print(f"Found {len(mbox_files)} MBOX file(s)")
            for mbox_file in mbox_files:
                self.parse_mbox_file(mbox_file)
        else:
            print(f"Error: {self.mbox_path} is not a valid file or directory")
    
    def get_summary(self) -> Dict:
        """Get a summary of the applications found."""
        return {
            'total_applications': len(self.applications),
            'unique_companies': len(self.unique_companies),
            'companies': sorted(list(self.unique_companies)),
            'applications': sorted(self.applications, key=lambda x: x['date'], reverse=True)
        }
    
    def print_summary(self) -> None:
        """Print a formatted summary of internship applications."""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("INTERNSHIP APPLICATION SUMMARY")
        print("="*60)
        print(f"\nTotal Applications: {summary['total_applications']}")
        print(f"Unique Companies: {summary['unique_companies']}")
        
        if summary['companies']:
            print(f"\nCompanies Applied To:")
            for company in summary['companies']:
                count = sum(1 for app in self.applications if app['company'] == company)
                print(f"  - {company}: {count} application(s)")
        
        if summary['applications']:
            print(f"\nAll Applications ({len(summary['applications'])} total):")
            for app in summary['applications']:
                print(f"  [{app['date']}] {app['company']}")
                print(f"    Subject: {app['subject'][:100]}")
        
        print("\n" + "="*60)


def main():
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Parse Google Takeout emails and count internship applications'
    )
    parser.add_argument(
        'mbox_path',
        type=str,
        help='Path to MBOX file or directory containing MBOX files'
    )
    
    args = parser.parse_args()
    
    # Check if path exists
    if not os.path.exists(args.mbox_path):
        print(f"Error: Path '{args.mbox_path}' does not exist")
        return
    
    # Create counter and parse
    counter = InternshipApplicationCounter(args.mbox_path)
    counter.parse()
    counter.print_summary()


if __name__ == '__main__':
    main()

