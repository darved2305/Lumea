import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './ServicesSection.css'

gsap.registerPlugin(ScrollTrigger)

function ServicesSection() {
  useEffect(() => {
    const cards = document.querySelectorAll('.service-card')
    cards.forEach((card, index) => {
      gsap.fromTo(card,
        {
          opacity: 0,
          y: 60,
        },
        {
          opacity: 1,
          y: 0,
          duration: 1,
          delay: index * 0.1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: card,
            start: 'top 85%',
            toggleActions: 'play none none reverse'
          }
        }
      )
    })

    const title = document.querySelector('.services-title')
    if (title) {
      gsap.fromTo(title,
        { opacity: 0, y: -50 },
        {
          opacity: 1,
          y: 0,
          duration: 1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: title,
            start: 'top 85%'
          }
        }
      )
    }

    const subtitle = document.querySelector('.services-subtitle')
    if (subtitle) {
      gsap.fromTo(subtitle,
        { opacity: 0, y: -30 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          delay: 0.2,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: subtitle,
            start: 'top 85%'
          }
        }
      )
    }
  }, [])

  const { t } = useTranslation()

  return (
    <section className="services">
      <div className="services-container">
        <motion.div 
          className="services-header"
          initial={{ opacity: 0, y: -40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="services-title">{t('services.title')}</h2>
          <p className="services-subtitle">
            {t('services.subtitle')}
          </p>
        </motion.div>

        <div className="services-grid">
          <div className="service-card card-left-top">
            <h3 className="service-title">{t('services.cards.preventive.title')}</h3>
            <p className="service-description">
              {t('services.cards.preventive.description')}
            </p>
          </div>

          <div className="petal-container">
            <div className="petal petal-green top-left" />
            <div className="petal petal-brown top-right" />
            <div className="petal petal-brown bottom-left" />
            <div className="petal petal-green bottom-right" />
            <div className="petal-border horizontal-top" />
            <div className="petal-border horizontal-bottom" />
            <div className="petal-border vertical-left" />
            <div className="petal-border vertical-right" />
          </div>

          <div className="service-card card-right-top">
            <h3 className="service-title">{t('services.cards.tracking.title')}</h3>
            <p className="service-description">
              {t('services.cards.tracking.description')}
            </p>
          </div>

          <div className="service-card card-left-bottom">
            <h3 className="service-title">{t('services.cards.reminders.title')}</h3>
            <p className="service-description">
              {t('services.cards.reminders.description')}
            </p>
          </div>

          <div className="service-card card-right-bottom">
            <h3 className="service-title">{t('services.cards.index.title')}</h3>
            <p className="service-description">
              {t('services.cards.index.description')}
            </p>
          </div>
        </div>

        <motion.div 
          className="services-footer"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          <motion.a 
            href="#" 
            className="btn-learn-more"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 10 }}
          >
            Learn More
          </motion.a>
        </motion.div>
      </div>
    </section>
  )
}

export default ServicesSection
