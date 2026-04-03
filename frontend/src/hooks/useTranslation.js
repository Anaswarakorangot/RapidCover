/**
 * useTranslation.js  –  Minimal i18n hook for partner-facing UI
 *
 * Reads user.language_pref from AuthContext and returns a t(key) function.
 * Falls back to English for any unsupported language.
 *
 * Supported: en, hi, ta, kn, te, mr, bn
 *
 * Usage:
 *   const { t, lang } = useTranslation();
 *   <p>{t('dashboard.hello')}</p>
 */

import { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';

// ── Translations ──────────────────────────────────────────────────────────────

const STRINGS = {
  en: {
    // Navigation
    'nav.dashboard': 'Home',
    'nav.policy':    'Policy',
    'nav.claims':    'Claims',
    'nav.profile':   'Profile',

    // Dashboard
    'dashboard.hello':        'Hello',
    'dashboard.covered':      'Covered',
    'dashboard.live':         '🔄 Live',
    'dashboard.active_policy': 'Active Policy',
    'dashboard.no_policy':    'No Active Policy',
    'dashboard.get_coverage': 'Get Coverage',
    'dashboard.days_left':    'Days Left',
    'dashboard.daily_payout': 'Daily Payout',
    'dashboard.max_days':     'Max Days/Wk',
    'dashboard.zone_info':    'Set your zone in profile',
    'dashboard.earnings':     'Earnings',
    'dashboard.total_recv':   'Total Received',
    'dashboard.pending':      'Pending',
    'dashboard.recent_claims': 'Recent Claims',
    'dashboard.view_all':     'View All →',
    'dashboard.quick_actions': 'Quick Actions',
    'dashboard.view_policy':  'View Policy',
    'dashboard.claim_history': 'Claim History',
    'dashboard.covered_for':  'You\'re covered for:',

    // Reassignment card
    'reassign.title':   'Zone Reassignment',
    'reassign.body':    'Your delivery zone is changing.',
    'reassign.accept':  'Accept New Zone',
    'reassign.decline': 'Decline',
    'reassign.processing': 'Processing…',

    // Policy
    'policy.active':          'Active',
    'policy.grace_period':    'Grace Period',
    'policy.lapsed':          'Lapsed',
    'policy.cancelled':       'Cancelled',
    'policy.expires_in':      'Expires in',
    'policy.days':            'days',
    'policy.expires_today':   'Expires today',
    'policy.expires_tomorrow':'Expires tomorrow',
    'policy.grace_left':      'Grace period:',
    'policy.hours_left':      'h left',
    'policy.renew':           'Renew',
    'policy.cancel':          'Cancel',
    'policy.certificate':     'Certificate',

    // Claims
    'claims.paid':      'Paid',
    'claims.approved':  'Approved',
    'claims.pending':   'Pending',
    'claims.rejected':  'Rejected',
    'claims.no_claims': 'No claims yet',
    'claims.empty_sub': 'Claims appear here when a trigger fires in your zone.',
    'claims.upi_ref':   'UPI Ref',

    // Disruption types
    'trigger.rain':     'Heavy Rain',
    'trigger.heat':     'Extreme Heat',
    'trigger.aqi':      'Dangerous AQI',
    'trigger.shutdown': 'Civic Shutdown',
    'trigger.closure':  'Store Closure',

    // General
    'btn.save':    'Save',
    'btn.cancel':  'Cancel',
    'btn.edit':    'Edit',
    'btn.logout':  'Logout',
    'payout.sent': 'Money Sent!',
  },

  hi: {
    'nav.dashboard': 'होम',
    'nav.policy':    'पॉलिसी',
    'nav.claims':    'दावे',
    'nav.profile':   'प्रोफ़ाइल',

    'dashboard.hello':         'नमस्ते',
    'dashboard.covered':       'कवर्ड',
    'dashboard.live':          '🔄 लाइव',
    'dashboard.active_policy': 'सक्रिय पॉलिसी',
    'dashboard.no_policy':     'कोई सक्रिय पॉलिसी नहीं',
    'dashboard.get_coverage':  'कवरेज लें',
    'dashboard.days_left':     'दिन शेष',
    'dashboard.daily_payout':  'दैनिक भुगतान',
    'dashboard.max_days':      'अधिकतम दिन/सप्ताह',
    'dashboard.zone_info':     'प्रोफ़ाइल में ज़ोन सेट करें',
    'dashboard.earnings':      'कमाई',
    'dashboard.total_recv':    'कुल प्राप्त',
    'dashboard.pending':       'लंबित',
    'dashboard.recent_claims': 'हालिया दावे',
    'dashboard.view_all':      'सभी देखें →',
    'dashboard.quick_actions': 'त्वरित कार्य',
    'dashboard.view_policy':   'पॉलिसी देखें',
    'dashboard.claim_history': 'दावा इतिहास',
    'dashboard.covered_for':   'आप इनके लिए कवर हैं:',

    'reassign.title':      'ज़ोन परिवर्तन',
    'reassign.body':       'आपका डिलीवरी ज़ोन बदल रहा है।',
    'reassign.accept':     'नया ज़ोन स्वीकार करें',
    'reassign.decline':    'अस्वीकार करें',
    'reassign.processing': 'प्रोसेसिंग…',

    'policy.active':           'सक्रिय',
    'policy.grace_period':     'ग्रेस अवधि',
    'policy.lapsed':           'समाप्त',
    'policy.cancelled':        'रद्द',
    'policy.expires_in':       'में समाप्त',
    'policy.days':             'दिन',
    'policy.expires_today':    'आज समाप्त हो रही है',
    'policy.expires_tomorrow': 'कल समाप्त हो रही है',
    'policy.grace_left':       'ग्रेस अवधि:',
    'policy.hours_left':       'घंटे शेष',
    'policy.renew':            'नवीनीकृत करें',
    'policy.cancel':           'रद्द करें',
    'policy.certificate':      'प्रमाणपत्र',

    'claims.paid':      'भुगतान हुआ',
    'claims.approved':  'स्वीकृत',
    'claims.pending':   'लंबित',
    'claims.rejected':  'अस्वीकृत',
    'claims.no_claims': 'अभी कोई दावा नहीं',
    'claims.empty_sub': 'जब आपके ज़ोन में कोई ट्रिगर होगा तो दावे यहाँ दिखेंगे।',
    'claims.upi_ref':   'UPI संदर्भ',

    'trigger.rain':     'भारी बारिश',
    'trigger.heat':     'अत्यधिक गर्मी',
    'trigger.aqi':      'खतरनाक AQI',
    'trigger.shutdown': 'नागरिक शटडाउन',
    'trigger.closure':  'स्टोर बंद',

    'btn.save':    'सहेजें',
    'btn.cancel':  'रद्द करें',
    'btn.edit':    'संपादित करें',
    'btn.logout':  'लॉग आउट',
    'payout.sent': 'पैसे भेज दिए!',
  },

  ta: {
    'nav.dashboard': 'முகப்பு',
    'nav.policy':    'கொள்கை',
    'nav.claims':    'கோரிக்கைகள்',
    'nav.profile':   'சுயவிவரம்',
    'dashboard.hello': 'வணக்கம்',
    'dashboard.covered': 'பாதுகாக்கப்பட்டது',
    'dashboard.no_policy': 'செயலில் உள்ள கொள்கை இல்லை',
    'dashboard.get_coverage': 'கவரேஜ் பெறுக',
    'claims.paid':     'செலுத்தப்பட்டது',
    'claims.pending':  'நிலுவையில்',
    'claims.rejected': 'நிராகரிக்கப்பட்டது',
    'trigger.rain':    'கனமழை',
    'trigger.heat':    'அதிக வெப்பம்',
    'trigger.aqi':     'ஆபத்தான AQI',
    'trigger.shutdown':'குடிமக்கள் மூடல்',
    'trigger.closure': 'கடை மூடல்',
    'btn.save':   'சேமி',
    'btn.cancel': 'ரத்து செய்',
    'btn.logout': 'வெளியேறு',
    'reassign.accept':  'புதிய மண்டலத்தை ஏற்கவும்',
    'reassign.decline': 'மறுக்கவும்',
    'payout.sent': 'பணம் அனுப்பப்பட்டது!',
  },

  kn: {
    'nav.dashboard': 'ಮುಖಪುಟ',
    'nav.policy':    'ನೀತಿ',
    'nav.claims':    'ಹಕ್ಕುಗಳು',
    'nav.profile':   'ಪ್ರೊಫೈಲ್',
    'dashboard.hello': 'ನಮಸ್ಕಾರ',
    'dashboard.covered': 'ರಕ್ಷಿತ',
    'dashboard.no_policy': 'ಯಾವುದೇ ಪಾಲಿಸಿ ಇಲ್ಲ',
    'dashboard.get_coverage': 'ಕವರೇಜ್ ಪಡೆಯಿರಿ',
    'claims.paid':     'ಪಾವತಿಸಲಾಗಿದೆ',
    'claims.pending':  'ಬಾಕಿ ಇದೆ',
    'claims.rejected': 'ನಿರಾಕರಿಸಲಾಗಿದೆ',
    'trigger.rain':    'ಭಾರೀ ಮಳೆ',
    'trigger.heat':    'ಅತಿ ಶಾಖ',
    'trigger.aqi':     'AQI ಅಪಾಯ',
    'trigger.shutdown':'ನಾಗರಿಕ ಮುಚ್ಚಡ',
    'trigger.closure': 'ಅಂಗಡಿ ಮುಚ್ಚಿದೆ',
    'btn.save':   'ಉಳಿಸಿ',
    'btn.cancel': 'ರದ್ದುಮಾಡಿ',
    'btn.logout': 'ಲಾಗ್ ಔಟ್',
    'reassign.accept':  'ಹೊಸ ವಲಯ ಒಪ್ಪಿಕೊಳ್ಳಿ',
    'reassign.decline': 'ನಿರಾಕರಿಸಿ',
    'payout.sent': 'ಹಣ ಕಳುಹಿಸಲಾಗಿದೆ!',
  },

  te: {
    'nav.dashboard': 'హోమ్',
    'nav.policy':    'పాలసీ',
    'nav.claims':    'క్లెయిమ్‌లు',
    'nav.profile':   'ప్రొఫైల్',
    'dashboard.hello': 'నమస్కారం',
    'dashboard.covered': 'కవర్ చేయబడింది',
    'dashboard.no_policy': 'చురుకైన పాలసీ లేదు',
    'dashboard.get_coverage': 'కవరేజ్ పొందండి',
    'claims.paid':     'చెల్లించబడింది',
    'claims.pending':  'పెండింగ్',
    'claims.rejected': 'తిరస్కరించబడింది',
    'trigger.rain':    'భారీ వర్షం',
    'trigger.heat':    'అధిక వేడి',
    'trigger.aqi':     'ప్రమాదకరమైన AQI',
    'trigger.shutdown':'పౌర మూసివేత',
    'trigger.closure': 'స్టోర్ మూసివేత',
    'btn.save':   'సేవ్ చేయి',
    'btn.cancel': 'రద్దు చేయి',
    'btn.logout': 'లాగ్ అవుట్',
    'reassign.accept':  'కొత్త జోన్ అంగీకరించు',
    'reassign.decline': 'తిరస్కరించు',
    'payout.sent': 'డబ్బు పంపబడింది!',
  },

  mr: {
    'nav.dashboard': 'मुखपृष्ठ',
    'nav.policy':    'धोरण',
    'nav.claims':    'दावे',
    'nav.profile':   'प्रोफाइल',
    'dashboard.hello': 'नमस्कार',
    'dashboard.covered': 'संरक्षित',
    'dashboard.no_policy': 'कोणतीही सक्रिय पॉलिसी नाही',
    'dashboard.get_coverage': 'कव्हरेज मिळवा',
    'claims.paid':     'भुगतान झाले',
    'claims.pending':  'प्रलंबित',
    'claims.rejected': 'नाकारले',
    'trigger.rain':    'जड पाऊस',
    'trigger.heat':    'अति उष्णता',
    'trigger.aqi':     'धोकादायक AQI',
    'trigger.shutdown':'नागरी बंद',
    'trigger.closure': 'दुकान बंद',
    'btn.save':   'जतन करा',
    'btn.cancel': 'रद्द करा',
    'btn.logout': 'लॉग आउट',
    'reassign.accept':  'नवीन झोन स्वीकारा',
    'reassign.decline': 'नाकारा',
    'payout.sent': 'पैसे पाठवले!',
  },

  bn: {
    'nav.dashboard': 'হোম',
    'nav.policy':    'পলিসি',
    'nav.claims':    'দাবি',
    'nav.profile':   'প্রোফাইল',
    'dashboard.hello': 'নমস্কার',
    'dashboard.covered': 'সুরক্ষিত',
    'dashboard.no_policy': 'কোনো সক্রিয় পলিসি নেই',
    'dashboard.get_coverage': 'কভারেজ নিন',
    'claims.paid':     'পরিশোধ হয়েছে',
    'claims.pending':  'অপেক্ষমাণ',
    'claims.rejected': 'প্রত্যাখ্যাত',
    'trigger.rain':    'ভারী বৃষ্টি',
    'trigger.heat':    'অত্যধিক গরম',
    'trigger.aqi':     'বিপজ্জনক AQI',
    'trigger.shutdown':'নাগরিক বন্ধ',
    'trigger.closure': 'দোকান বন্ধ',
    'btn.save':   'সংরক্ষণ',
    'btn.cancel': 'বাতিল',
    'btn.logout': 'লগ আউট',
    'reassign.accept':  'নতুন জোন গ্রহণ করুন',
    'reassign.decline': 'প্রত্যাখ্যান করুন',
    'payout.sent': 'টাকা পাঠানো হয়েছে!',
  },
};

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * useTranslation – returns `t(key)` for the partner's preferred language.
 *
 * @returns {{ t: (key: string) => string, lang: string }}
 */
export default function useTranslation() {
  const { user } = useAuth();
  const lang = user?.language_pref?.slice(0, 2) || 'en';

  const t = useMemo(() => {
    const dict = STRINGS[lang] || {};
    const en   = STRINGS.en;
    return (key) => dict[key] ?? en[key] ?? key;
  }, [lang]);

  return { t, lang };
}
