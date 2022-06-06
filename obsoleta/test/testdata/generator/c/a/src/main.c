#include "obsoleta_a.h"
#include "b.h"
#include <stdio.h>
#include <string.h>


int main()
{
    printf("\n------ starting a (C) -------\n");
    
    // take a tour through both b and c to pretend it is libraries 
    // that actually have a meaningful purpose
    printf("Testing add method in a, b and c: 1+1+1=%i\n\n", b_add(1));
    
    obsoleta_entry_a(OBSOLETA_INFO);
    printf("\n\n");
    
    const char* check = obsoleta_entry_a(OBSOLETA_CHECK);
    
    if (strlen(check))
    {
        printf("version check for package %s : FAIL\n", check);
        return 1;
    }
    
    printf("version check for %s : PASS\n", obsoleta_entry_a(OBSOLETA_NAME));
    return 0;
}
