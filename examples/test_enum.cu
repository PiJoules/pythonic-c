enum day {MON, TUE, WED, THU,
          FRI, SAT, SUN}

def main():
    d = WED
    switch d:
        case MON:
            printf("MON\n")
            break
        case TUE:
            printf("TUE\n")
            break
        case WED:
            printf("WED\n")
            break
        case THU:
            printf("THU\n")
            break
        case FRI:
            printf("FRI\n")
            break
        case SAT:
            printf("SAT\n")
            break
        case SUN:
            printf("SUN\n")
            break
        else:
            printf("Unknown day\n")
    

    return 0
