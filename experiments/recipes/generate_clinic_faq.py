"""Generate synthetic FAQs for a fictional clinic. Do not use as real clinic advice."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'faq-bot-hinglish'

# Each tuple is English, Roman Hinglish and Devanagari topic followed by a
# corresponding fictional administrative answer in each language.
FAQ = (
 ('opening hours', 'clinic timing', 'क्लिनिक की टाइमिंग', 'The sample clinic is open from 9 am to 5 pm.', 'Sample clinic subah 9 se shaam 5 baje tak khula hai.', 'सैंपल क्लिनिक सुबह 9 से शाम 5 बजे तक खुला है।'),
 ('open days', 'clinic ke open days', 'क्लिनिक के खुले दिन', 'The sample clinic opens Monday to Saturday.', 'Sample clinic Monday se Saturday khulta hai.', 'सैंपल क्लिनिक सोमवार से शनिवार खुलता है।'),
 ('Sunday opening', 'Sunday opening', 'रविवार की ओपनिंग', 'The sample clinic is closed on Sundays.', 'Sample clinic Sunday ko band rehta hai.', 'सैंपल क्लिनिक रविवार को बंद रहता है।'),
 ('booking appointments', 'appointment booking', 'अपॉइंटमेंट बुकिंग', 'Book an appointment at the reception desk.', 'Appointment reception desk par book kar sakte hain.', 'अपॉइंटमेंट रिसेप्शन डेस्क पर बुक कर सकते हैं।'),
 ('rescheduling an appointment', 'appointment reschedule', 'अपॉइंटमेंट की तारीख बदलने', 'Ask reception to change the appointment date.', 'Appointment ki date badalne ke liye reception se baat karein.', 'अपॉइंटमेंट की तारीख बदलने के लिए रिसेप्शन से बात करें।'),
 ('cancelling an appointment', 'appointment cancellation', 'अपॉइंटमेंट रद्द करने', 'Ask reception to cancel an appointment.', 'Appointment cancel karne ke liye reception se baat karein.', 'अपॉइंटमेंट रद्द करने के लिए रिसेप्शन से बात करें।'),
 ('walk-in visits', 'walk-in visit', 'बिना बुकिंग विजिट', 'Walk-ins are subject to appointment availability.', 'Walk-in visit appointment availability par depend karti hai.', 'बिना बुकिंग विजिट अपॉइंटमेंट की उपलब्धता पर निर्भर है।'),
 ('online consultations', 'online consultation', 'ऑनलाइन कंसल्टेशन', 'Online consultations are available by appointment.', 'Online consultation appointment se available hai.', 'ऑनलाइन कंसल्टेशन अपॉइंटमेंट से उपलब्ध है।'),
 ('consultation fee', 'consultation fee', 'कंसल्टेशन फीस', 'The sample consultation fee is 400 rupees.', 'Sample consultation ki fee 400 rupaye hai.', 'सैंपल कंसल्टेशन फीस 400 रुपये है।'),
 ('payment methods', 'payment methods', 'भुगतान के तरीके', 'The sample clinic accepts cash and UPI.', 'Sample clinic cash aur UPI accept karta hai.', 'सैंपल क्लिनिक नकद और यूपीआई स्वीकार करता है।'),
 ('payment receipts', 'payment receipt', 'पेमेंट रसीद', 'Ask reception for a payment receipt.', 'Payment receipt ke liye reception se poochhein.', 'भुगतान की रसीद के लिए रिसेप्शन से पूछें।'),
 ('report collection', 'report collection', 'रिपोर्ट लेने', 'Reports can be collected at reception during open hours.', 'Report open hours mein reception se le sakte hain.', 'रिपोर्ट खुले समय में रिसेप्शन से ले सकते हैं।'),
 ('waiting times', 'waiting time', 'इंतजार का समय', 'Waiting time varies; ask reception for the current estimate.', 'Waiting time alag ho sakta hai; current estimate reception se poochhein.', 'इंतजार अलग हो सकता है; मौजूदा अनुमान रिसेप्शन से पूछें।'),
 ('visits by minors', 'bachchon ki visit', 'बच्चों की विजिट', 'A parent or guardian should accompany a minor.', 'Minor ke saath parent ya guardian aana chahiye.', 'नाबालिग के साथ अभिभावक आना चाहिए।'),
 ('available languages', 'available languages', 'उपलब्ध भाषाओं', 'Reception can communicate in Hindi and English.', 'Reception Hindi aur English mein baat kar sakta hai.', 'रिसेप्शन हिंदी और अंग्रेजी में बात कर सकता है।'),
 ('wheelchair access', 'wheelchair access', 'व्हीलचेयर एक्सेस', 'The sample clinic has a step-free entrance.', 'Sample clinic mein step-free entrance hai.', 'सैंपल क्लिनिक में बिना सीढ़ियों वाला प्रवेश है।'),
 ('parking', 'parking', 'पार्किंग', 'The sample clinic has limited parking.', 'Sample clinic mein limited parking hai.', 'सैंपल क्लिनिक में सीमित पार्किंग है।'),
 ('follow-up appointments', 'follow-up appointment', 'फॉलो-अप अपॉइंटमेंट', 'Ask reception to arrange a follow-up appointment.', 'Follow-up appointment ke liye reception se baat karein.', 'फॉलो-अप अपॉइंटमेंट के लिए रिसेप्शन से बात करें।'),
 ('visitor privacy', 'visitor privacy', 'विजिटर प्राइवेसी', 'Ask reception about the sample clinic privacy policy.', 'Sample clinic ki privacy policy ke liye reception se poochhein.', 'सैंपल क्लिनिक की प्राइवेसी पॉलिसी के लिए रिसेप्शन से पूछें।'),
 ('receiving test reports online', 'online test report', 'ऑनलाइन टेस्ट रिपोर्ट', 'Ask reception whether your report can be shared online.', 'Apni report online mil sakti hai ya nahi, reception se poochhein.', 'आपकी रिपोर्ट ऑनलाइन मिल सकती है या नहीं, रिसेप्शन से पूछें।'),
)

TRAIN = (
 ('Could you tell me about {topic}?', 'Please explain {topic}.', 'I need information about {topic}.', 'Where can I find details about {topic}?', 'Can you share information about {topic}?'),
 ('Mujhe {topic} ke baare mein bata sakte hain?', 'Please {topic} ki information dein.', '{topic} ki details chahiye.', '{topic} ke baare mein kuch bataiye.', 'Kya aap {topic} ki jaankari de sakte hain?', '{topic} se judi information share karein.'),
 ('मुझे {topic} के बारे में बताएँ।', 'कृपया {topic} की जानकारी दें।', '{topic} की डिटेल चाहिए।', '{topic} के बारे में कुछ बताइए।'),
)
TEST = ('I have a question: what should I know about {topic}?', 'Ek sawaal hai: {topic} ke baare mein kya jaankari hai?', 'एक सवाल है: {topic} पर क्या जानकारी है?')


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    rows: dict[str, list[dict[str, str]]] = {'train': [], 'test': []}
    for item in FAQ:
        for language in range(3):
            topic, answer = item[language], item[language + 3]
            for pattern in TRAIN[language]:
                rows['train'].append({'question': pattern.format(topic=topic), 'answer': answer})
            rows['test'].append({'question': TEST[language].format(topic=topic), 'answer': answer})
    for split, items in rows.items():
        with (ROOT / f'{split}.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['question', 'answer'])
            writer.writeheader()
            writer.writerows(items)
        print(f'{split}: {len(items)} examples')


if __name__ == '__main__':
    main()
