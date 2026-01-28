import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import './HowWeCanHelp.css'

function HowWeCanHelp() {
  const { t } = useTranslation()
  
  const services = [
    {
      icon: (
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <circle cx="40" cy="40" r="15" fill="#4a7c59" />
          <circle cx="40" cy="40" r="20" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <circle cx="40" cy="40" r="25" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <circle cx="40" cy="40" r="30" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <circle cx="40" cy="40" r="35" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
        </svg>
      ),
      title: t('howItWorks.features.ocr.title'),
      description: t('howItWorks.features.ocr.description')
    },
    {
      icon: (
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <rect x="30" y="30" width="20" height="20" fill="#4a7c59" />
          <rect x="25" y="25" width="30" height="30" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <rect x="20" y="20" width="40" height="40" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <rect x="15" y="15" width="50" height="50" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
        </svg>
      ),
      title: t('howItWorks.features.reminders.title'),
      description: t('howItWorks.features.reminders.description')
    },
    {
      icon: (
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <path d="M40 20 L55 50 L25 50 Z" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <path d="M40 25 L52 47 L28 47 Z" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <path d="M40 30 L49 44 L31 44 Z" stroke="#4a7c59" strokeWidth="1.5" fill="none" />
          <path d="M40 35 L46 41 L34 41 Z" fill="#4a7c59" />
        </svg>
      ),
      title: t('howItWorks.features.index.title'),
      description: t('howItWorks.features.index.description')
    }
  ]

  return (
    <section className="how-we-help">
      <div className="how-we-help-container">
        <div className="help-header">
          <div className="help-text">
            <motion.h2 
              className="help-title"
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              {t('howItWorks.title')}
            </motion.h2>
            <motion.p 
              className="help-subtitle"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2, duration: 0.8 }}
            >
              {t('howItWorks.subtitle')}
            </motion.p>
          </div>
          <motion.div
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            <motion.a 
              href="#" 
              className="btn-view-all"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {t('howItWorks.cta')}
            </motion.a>
          </motion.div>
        </div>

        <div className="services-cards">
          {services.map((service, index) => (
            <motion.div 
              key={service.title}
              className="service-card-item"
              initial={{ opacity: 0, y: 60 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.15, duration: 0.8 }}
            >
              <div className="service-icon">{service.icon}</div>
              <h3 className="service-card-title">{service.title}</h3>
              <p className="service-card-description">{service.description}</p>
              <a href="#" className="service-view-link">
                <span className="view-icon">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M8 3L13 8M13 8L8 13M13 8H3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </span>
                View
              </a>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowWeCanHelp
