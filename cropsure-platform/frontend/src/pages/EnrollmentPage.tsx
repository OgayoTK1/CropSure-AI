import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import Header from '../components/Header';
import StepFarmerDetails from '../enrollment/StepFarmerDetails';
import StepGPSBoundary from '../enrollment/StepGPSBoundary';
import StepPaymentConfirmation from '../enrollment/StepPaymentConfirmation';
import { FarmerDetails, Coordinate } from '../types';

const EMPTY_FARMER: FarmerDetails = { fullName: '', phone: '', village: '', cropType: 'Maize' };

const EnrollmentPage: React.FC = () => {
  const { t } = useTranslation();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [farmerDetails, setFarmerDetails] = useState<FarmerDetails>(EMPTY_FARMER);
  const [boundary, setBoundary] = useState<Coordinate[]>([]);
  const [areaAcres, setAreaAcres] = useState(0);

  const reset = () => {
    setStep(1);
    setFarmerDetails(EMPTY_FARMER);
    setBoundary([]);
    setAreaAcres(0);
  };

  const steps = [t('enrollment.step1'), t('enrollment.step2'), t('enrollment.step3')];

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="max-w-lg mx-auto px-4 py-6">
        {/* Title */}
        <h1 className="text-2xl font-bold text-center text-gray-900 mb-6">
          {t('enrollment.title')}
        </h1>

        {/* Step indicator */}
        <div className="flex items-center mb-8">
          {steps.map((label, i) => {
            const num = i + 1;
            const active = num === step;
            const done = num < step;
            return (
              <React.Fragment key={num}>
                <div className="flex flex-col items-center gap-1 flex-1">
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ${
                      active
                        ? 'bg-primary text-white border-primary scale-110'
                        : done
                        ? 'bg-primary/20 text-primary border-primary/40'
                        : 'bg-white text-gray-400 border-gray-200'
                    }`}
                  >
                    {done ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      num
                    )}
                  </div>
                  <span className={`text-xs text-center leading-tight ${active ? 'text-primary font-semibold' : 'text-gray-400'}`}>
                    {label}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <div className={`h-0.5 flex-1 mx-1 mb-5 rounded ${done ? 'bg-primary/40' : 'bg-gray-200'}`} />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Step content */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          {step === 1 && (
            <StepFarmerDetails
              initial={farmerDetails}
              onNext={(d) => { setFarmerDetails(d); setStep(2); }}
            />
          )}
          {step === 2 && (
            <StepGPSBoundary
              onConfirm={(b, a) => { setBoundary(b); setAreaAcres(a); setStep(3); }}
              onBack={() => setStep(1)}
            />
          )}
          {step === 3 && (
            <StepPaymentConfirmation
              farmerDetails={farmerDetails}
              boundary={boundary}
              areaAcres={areaAcres}
              onBack={() => setStep(2)}
              onReset={reset}
            />
          )}
        </div>
      </main>
    </div>
  );
};

export default EnrollmentPage;