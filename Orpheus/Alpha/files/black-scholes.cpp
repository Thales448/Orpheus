#include <iostream>
#include <cmath>
#include <random>

double iota(double x) {
    return 0.5*std::erfc(-x * M_SQRT1_2);
}

double blackScholesCall(double S, double K, double T, double r, double sigma) {
    double d1 = (std::log(S / K) + (r + (sigma * sigma / 2) *T)/ (sigma * std::sqrt(T)));
    double d2 = d1 - sigma * std::sqrt(T);
    return S*iota(d1) - (K * std::exp(-r*T)*iota(d2));
}

double blackScholesPut(double S, double K, double T, double r, double sigma) {
    double d1 = (std::log(S / K) + ( r + sigma*sigma / 2 )*T) / (sigma * std::sqrt(T));
    double d2 = d1 - sigma * std::sqrt(T);
    return (K * std::exp(-r*T)*iota(-d2) - S * iota(-d1));
}

int main() {
    double S, K, T, r, sigma;
    // Hardcode variables for testing
    S = 594.20;      // Current Underlying Price
    K = 589;      // Strike Price
    T = 4.0/252.0;        // Time to Expiry (in years)
    r = .0413;       // Risk-Free Rate
    sigma = 0.1489;    // Volatility

    // You can change any of the above values to see how prices change
    // For example, to test different volatilities:
    // sigma = 0.3;
    
    // std::cout<<"Current Underlying Price (S): ";
    // std::cin>>S;
    // std::cout<<"Strike Price (K): ";
    // std::cin>>K;
    // std::cout<<"DTE (T): ";
    // std::cin>>T;
    // std::cout<<"Risk-Free Rate (r): ";
    // std::cin>>r;
    // std::cout<<"Volatility (sigma): ";
    // std::cin>>sigma;

    double callPrice = blackScholesCall(S, K, T, r, sigma);
    double putPrice = blackScholesPut(S, K, T, r, sigma);

    std::cout<<"Call Option Price: "<<callPrice<<std::endl;
    std::cout<<"Put Option Price: "<<putPrice<<std::endl;

    return 0;
    
    }