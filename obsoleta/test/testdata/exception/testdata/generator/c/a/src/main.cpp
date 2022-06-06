#include "obsoleta_a.h"
#include <iostream>


int main()
{
    std::cout << "\n------ starting a (C++) -------\n";
    
    Obsoleta_a::info();
    std::cout << "\n\n";
    
    std::string check = Obsoleta_a::check();
    
    if (check.length())
    {
        std::cout << "version check for package " << check << " : FAIL\n";
        return 1;
    }
    
    std::cout << "version check for " << Obsoleta_a::name() << " : PASS\n";
    return 0;
}
