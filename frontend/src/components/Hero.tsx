import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import gsap from 'gsap'
import './Hero.css'

function Hero() {
  const { t } = useTranslation()
  const imagesRef = useRef<(HTMLDivElement | null)[]>([])
  
  useEffect(() => {
    imagesRef.current.forEach((img, index) => {
      if (img) {
        gsap.fromTo(img,
          {
            opacity: 0,
            scale: 0.5,
            rotation: index % 2 === 0 ? -180 : 180
          },
          {
            opacity: 1,
            scale: 1,
            rotation: 0,
            duration: 1.5,
            delay: 0.5 + index * 0.2,
            ease: 'elastic.out(1, 0.5)'
          }
        )

        gsap.to(img, {
          y: index % 2 === 0 ? -15 : 15,
          duration: 2.5 + index * 0.5,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut'
        })
      }
    })
  }, [])

  return (
    <section className="hero">
      <div className="hero-container">
        <motion.div 
          className="hero-content"
          initial={{ opacity: 0, x: -100 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 1, ease: 'easeOut' }}
        >
          <motion.h1 
            className="hero-title"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          >
            {t('hero.tagline')}
            <br />
            is <motion.span 
              className="highlight"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.8, duration: 0.6, type: 'spring', stiffness: 200 }}
            >
              {t('hero.taglineHighlight')}
            </motion.span>
            <br />
            <motion.span 
              className="highlight"
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 1, duration: 0.6, type: 'spring', stiffness: 200 }}
            >
              {t('hero.subtitle')}
            </motion.span>
          </motion.h1>
          <motion.p 
            className="hero-description"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.8 }}
          >
            {t('hero.description')}
          </motion.p>
          <motion.p 
            className="hero-disclaimer"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2, duration: 0.8 }}
          >
            {t('hero.disclaimer')}
          </motion.p>
          <motion.div 
            className="hero-buttons"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.3, duration: 0.8 }}
          >
            <motion.a 
              href="#" 
              className="btn-primary"
              whileHover={{ scale: 1.1, y: -3, boxShadow: '0 10px 30px rgba(74, 124, 89, 0.4)' }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 10 }}
            >
              {t('hero.cta.upload')}
            </motion.a>
            <motion.a 
              href="#" 
              className="btn-secondary"
              whileHover={{ scale: 1.05, x: 10 }}
              whileTap={{ scale: 0.95 }}
            >
              <motion.span 
                className="btn-icon"
                whileHover={{ rotate: 90 }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 1L11 6M11 6L6 11M11 6H1" stroke="#2d2d2d" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </motion.span>
              {t('hero.cta.howItWorks')}
            </motion.a>
          </motion.div>
        </motion.div>
        <div className="hero-images">
          <div className="image-grid">
            <motion.div 
              className="image-item image-1"
              ref={el => imagesRef.current[0] = el}
              whileHover={{ scale: 1.15, rotate: 5, zIndex: 10 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <img src="https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&h=300&fit=crop" alt={t('hero.images.labReport')} />
            </motion.div>
            <motion.div 
              className="image-item image-2"
              ref={el => imagesRef.current[1] = el}
              whileHover={{ scale: 1.15, rotate: -5, zIndex: 10 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <img src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=400&h=300&fit=crop" alt={t('hero.images.dashboard')} />
            </motion.div>
            <motion.div 
              className="image-item image-3"
              ref={el => imagesRef.current[2] = el}
              whileHover={{ scale: 1.15, rotate: 5, zIndex: 10 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <img src="https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=400&h=300&fit=crop" alt={t('hero.images.smartwatch')} />
            </motion.div>
            <motion.div 
              className="image-item image-4"
              ref={el => imagesRef.current[3] = el}
              whileHover={{ scale: 1.15, rotate: -5, zIndex: 10 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <img src="https://images.unsplash.com/photo-1587854692152-cbe660dbde88?w=400&h=300&fit=crop" alt={t('hero.images.medicine')} />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Hero
