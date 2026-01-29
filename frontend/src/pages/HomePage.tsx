import Header from '../components/Header'
import Hero from '../components/Hero'
import ServicesSection from '../components/ServicesSection'
import HowWeCanHelp from '../components/HowWeCanHelp'
import BeliefStatement from '../components/BeliefStatement'
import Testimonials from '../components/Testimonials'
import ArtOfNaturalRemedies from '../components/ArtOfNaturalRemedies'
import Footer from '../components/Footer'

function HomePage() {
  return (
    <div className="app">
      <Header />
      <main>
        <Hero />
        <ServicesSection />
        <HowWeCanHelp />
        <BeliefStatement />
        <Testimonials />
        <ArtOfNaturalRemedies />
      </main>
      <Footer />
    </div>
  )
}

export default HomePage
