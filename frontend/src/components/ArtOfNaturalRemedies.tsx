import { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import './ArtOfNaturalRemedies.css'

function ArtOfNaturalRemedies() {
  const { t } = useTranslation()
  const [openAccordion, setOpenAccordion] = useState<number | null>(null)

  const accordionItems = [
    {
      question: t('faq.items.isDoctor.question'),
      answer: t('faq.items.isDoctor.answer')
    },
    {
      question: t('faq.items.reports.question'),
      answer: t('faq.items.reports.answer')
    },
    {
      question: t('faq.items.ocr.question'),
      answer: t('faq.items.ocr.answer')
    },
    {
      question: t('faq.items.reminders.question'),
      answer: t('faq.items.reminders.answer')
    },
    {
      question: t('faq.items.security.question'),
      answer: t('faq.items.security.answer')
    },
    {
      question: t('faq.items.export.question'),
      answer: t('faq.items.export.answer')
    }
  ]

  const toggleAccordion = (index: number) => {
    setOpenAccordion(openAccordion === index ? null : index)
  }

  return (
    <section className="art-remedies">
      <div className="art-remedies-container">
        <div className="art-content">
          <motion.h2 
            className="art-title"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            {t('faq.title')} <span className="title-highlight">{t('faq.titleHighlight')}</span>
          </motion.h2>

          <motion.p 
            className="art-subtitle"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.8 }}
          >
            {t('faq.subtitle')}
          </motion.p>

          <div className="accordion-container">
            {accordionItems.map((item, index) => (
              <motion.div 
                key={index}
                className="accordion-item"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 + index * 0.1, duration: 0.8 }}
              >
                <button 
                  className="accordion-button"
                  onClick={() => toggleAccordion(index)}
                  aria-expanded={openAccordion === index}
                >
                  <span className="accordion-question">{item.question}</span>
                  <span className={`accordion-icon ${openAccordion === index ? 'open' : ''}`}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </span>
                </button>
                {openAccordion === index && (
                  <motion.div 
                    className="accordion-content"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <p className="accordion-answer">{item.answer}</p>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        <div className="art-images">
          <div className="images-grid">
            <motion.div 
              className="art-image-item image-1"
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2, duration: 0.6 }}
            >
              <img src="https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&h=300&fit=crop" alt="Medical professional analyzing data" />
            </motion.div>
            <motion.div 
              className="art-image-item image-2"
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3, duration: 0.6 }}
            >
              <img src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=400&h=300&fit=crop" alt="Health checkup consultation" />
            </motion.div>
            <motion.div 
              className="art-image-item image-3"
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4, duration: 0.6 }}
            >
              <img src="https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=400&h=300&fit=crop" alt="Preventive healthcare planning" />
            </motion.div>
            <motion.div 
              className="art-image-item image-4"
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.5, duration: 0.6 }}
            >
              <img 
                src="https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=400&h=300&fit=crop" 
                alt="Digital health records" 
                onError={(e) => {
                  e.currentTarget.src = 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&h=300&fit=crop'
                }}
              />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ArtOfNaturalRemedies
